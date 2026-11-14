"""QE Sign Stage: Release readiness review and Gate 5 sign-off."""
from __future__ import annotations

import json
from backend.core import documents
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.trace import _defect_body
from backend.qe import model
from backend.qe.validity import bundle


def _static_body(state: dict, run_id: str) -> str:
    s, check = state["summary"], state.get("plugin_check_5") or {}
    by = ", ".join(f"{k} {v}" for k, v in s["by_check"].items())
    return (f"## Verdict: {s['verdict']}\n\n{s['reason']}.\n\n| Metric | Value |\n|---|---|\n| Requirements | {s['requirements']} |\n| Requirements with a valid test | {s['requirements_with_valid_test']} |\n| Cases | {s['cases']} |\n"
            f"| Tests | {s['tests']} |\n| Valid | {s['valid']} |\n| Need review | {s['needs_review']} |\n| Failed checks | {by} |\n\n## Coverage gaps\n\n{', '.join(s['gaps']) or 'None'}\n\n"
            f"## Download and run\n\nDownload the tests at `/api/runs/{run_id}/tests.zip`. {state['run_command_text']}\n\n## Plugin Gate 5 check\n\n{check.get('note', '')}. "
            f"{check.get('error') or ''}" + "".join(f"\n- {g}" for g in check.get("not_applicable", [])[:20]) + f"\n\nBranch with generated tests: `{state.get('branch', '')}`\n")


async def qe_sign(rc: RunContext, state: dict) -> dict:
    if state.get("mode") == "brownfield":
        command = bundle.run_command(state.get("framework", ""))
        body = _static_body({**state, "run_command_text": f"From the repository root, with its dependencies installed, run `{command}`."}, rc.run_id)
        doc = documents.create(rc.project_id, "release", "Release Readiness: tests not executed", body, "system", data={"summary": state["summary"], "plugin_check": state.get("plugin_check_5")}, run_id=rc.run_id)
        return {"release_doc": doc["id"], "tests_zip": f"/api/runs/{rc.run_id}/tests.zip", "run_command": command}
    s = state["summary"]
    call = AgentCall(rc.run_id, rc.project_id, "confidence-reviewer")
    review = await call.typed(f"Independently review release readiness from this evidence only.\nSUMMARY:\n{json.dumps(s)}\nDEFECTS:\n{json.dumps(state.get('defects', []))[:6000]}\nHEALER LOG:\n{json.dumps(state.get('healer_log', []))}\nPLAN REVIEW:\n{json.dumps(state.get('plan_review'))}", model.ConfidenceReview)
    body = (f"## Verdict: {s['verdict']}\n\n| Metric | Value |\n|---|---|\n| Tests executed | {s['executed']} |\n| Passed | {s['passed']} |\n| Failed | {s['failed']} |\n| Pass rate | {s['pass_rate']}% |\n"
            f"| Requirements covered | {s['requirements_covered']}/{s['requirements']} ({s['coverage']}%) |\n| Application defects | {s['defects']} |\n| Independent review | {review.score} ({review.verdict}) |\n\n"
            f"## Coverage gaps\n\n{', '.join(s['gaps']) or 'None'}\n\n## Review issues\n\n" + ("\n".join(f"- {i}" for i in review.issues) or "None") + "\n\n## Defect records\n\n" + _defect_body(state.get("defect_records", [])) + "\n\n## Execution summary\n\n" + (state.get("execution_summary") or {}).get("text", "No summary.") + "\n\n## Defects\n\n" + ("\n".join(f"- **{d['name']}**: {d['message'][:300]}" for d in state.get("defects", [])) or "None") + f"\n\nBranch with generated tests: `{state.get('branch', '')}`\n")
    doc = documents.create(rc.project_id, "release", "Production Release Readiness & Sign-Off", body, "agent:confidence-reviewer", data={"summary": s, "review": review.model_dump()}, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    return {"release_doc": doc["id"], "release_review": review.model_dump()}
