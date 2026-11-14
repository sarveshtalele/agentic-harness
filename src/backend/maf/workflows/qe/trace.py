"""QE Traceability Stage: Building requirement-to-test matrix, execution summary, and confidence capping."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.core import documents
from backend.maf.engine import RunContext
from backend.maf.workflows.qe.common import _cell
from backend.maf.workflows.qe.heal import _records
from backend.qe import confidence, execution, plugin_bridge, trace
from backend.qe.emit.subject import exercises_repository


import re

def _defect_body(records: list[dict]) -> str:
    if not records:
        return "No failed tests."
    rows = []
    for r in records:
        raw_test = r.get("test", "")
        test_name = re.sub(r"^.*?tests[./\\]+", "", raw_test).lstrip(".:/") or raw_test
        rows.append(f"| {_cell(test_name)} | {r['classification']} | {_cell(r['evidence'][:200])} | {_cell(r['cause'])} | {_cell(r['fix'])} | {'yes' if r['healed'] else 'no'} |")
    return "| Test | Classification | Evidence | Cause | Fix | Healed |\n|---|---|---|---|---|---|\n" + "\n".join(rows)


def _static_rows(matrix: dict) -> str:
    lines = ["| Requirement | Priority | Cases | Test files | Validity |", "|---|---|---|---|---|"]
    for r in matrix["rows"]:
        lines.append(f"| {r['requirement_id']}: {_cell(r['title'])} | {r['priority']} | {', '.join(c['case_id'] for c in r['cases'])} | {_cell(', '.join(c['test_file'] or 'none' for c in r['cases']))} | "
                     + ", ".join(c["result"] + (f" ({'/'.join(c['failed_checks'])})" if c["failed_checks"] else "") for c in r["cases"]) + " |")
    return "\n".join(lines)


async def _plugin_gate5(rc: RunContext) -> dict:
    """The plugin's Gate 5 check, recorded. Its execution-result gaps are not failures here: no test is executed."""
    check = await asyncio.to_thread(plugin_bridge.check_gate, rc.project_id, plugin_bridge.app_name(rc.project_id), 5)
    note = "not applicable: tests are not executed here"
    return {"ok": None, "error": check.get("error"), "not_applicable": [f"{g} ({note})" for g in [*check.get("gaps", []), *check.get("missing", [])]], "note": note}


async def qe_trace_static(rc: RunContext, state: dict) -> dict:
    """Brownfield traceability without execution: the verdict is NOT EXECUTED, the counts are the validity result."""
    validation = state.get("validation")
    matrix = trace.static_matrix(state["requirements"], state["cases"], state.get("tests", []), validation)
    summary = trace.not_executed_summary(matrix, state["cases"], state.get("tests", []), validation)
    doc = documents.create(rc.project_id, "traceability", "Requirements-to-Test Traceability Matrix", _static_rows(matrix) + f"\n\nGaps (P0 and P1 requirements without a valid test): {matrix['gaps'] or 'none'}",
                           "system", data={"matrix": matrix, "summary": summary}, run_id=rc.run_id)
    plugin_check = await _plugin_gate5(rc)
    rc.log(f"Verdict {summary['verdict']}: {summary['valid']} of {summary['tests']} tests valid, {summary['requirements_with_valid_test']}/{summary['requirements']} requirements with a valid test", summary, "artifact")
    return {"matrix_doc": doc["id"], "summary": summary, "matrix": matrix, "plugin_check_5": plugin_check, "tests_review_after": state.get("tests_review"), "_next": "sign"}


async def qe_trace(rc: RunContext, state: dict) -> dict:
    if state.get("mode") == "brownfield":
        return await qe_trace_static(rc, state)
    results = state.get("results", [])
    defects = state.get("defects", [])
    matrix = trace.build_matrix(state["requirements"], state["cases"], state.get("tests", []), results)
    summary = trace.release_summary(matrix, results, defects)
    failed = [c for suite in results for c in suite["cases"] if c["status"] == "failed"]
    if failed and summary["passed"] == 0 and all(execution.classify_failure(c["message"]) == "ENVIRONMENT" for c in failed):
        summary |= {"verdict": "INCONCLUSIVE", "reason": "Tests could not run in this environment"}
    real = {t["path"] for t in state.get("tests", []) if state.get("worktree") and exercises_repository(Path(state["worktree"]), t["path"])}
    if reason := trace.no_product_run(state.get("mode", ""), matrix, real):
        summary |= {"verdict": "INCONCLUSIVE", "reason": reason}
    summary["failure_classes"] = execution.failure_counts(results)
    records = _records(results, state.get("defect_notes", {}), {r["test"].split("::")[-1] for r in state.get("defect_records", []) if r["healed"]})
    defect_doc = documents.create(rc.project_id, "defect_report", "Repository Defect Triaging & Anomaly Report", _defect_body(records), "system", data=records, run_id=rc.run_id)
    lines = ["| Requirement | Priority | Cases | Results | Covered |", "|---|---|---|---|---|"]
    for r in matrix["rows"]:
        lines.append(f"| {r['requirement_id']}: {_cell(r['title'])} | {r['priority']} | {', '.join(c['case_id'] for c in r['cases'])} | {', '.join(c['result'] for c in r['cases'])} | {'yes' if r['covered'] else 'NO'} |")
    doc = documents.create(rc.project_id, "traceability", "Requirements-to-Test Traceability Matrix", "\n".join(lines) + f"\n\nGaps: {matrix['gaps'] or 'none'}\n\nOrphan tests: {matrix['orphan_tests'] or 'none'}",
                           "system", data={"matrix": matrix, "summary": summary}, run_id=rc.run_id)
    rc.log(f"Verdict {summary['verdict']}: {summary['passed']}/{summary['executed']} passed, {summary['coverage']}% requirement coverage", summary, "artifact")
    executed = {c["case_id"]: c["result"] for row in matrix["rows"] for c in row["cases"]}
    after = confidence.cap_failed((state.get("tests_review") or {}).get("records", []), executed)
    rc.log(f"Test review after execution: score {after['score_before']} before, {after['score']} after; {after['capped']} of {after['executed']} executed tests failed and were capped at {confidence.TEST_FAIL_CAP}", {k: after[k] for k in ("score_before", "score", "capped", "failed", "executed")}, "review")
    return {"matrix_doc": doc["id"], "summary": summary, "tests_review_after": after, "defect_records": records, "defect_doc": defect_doc["id"], "_next": "sign"}
