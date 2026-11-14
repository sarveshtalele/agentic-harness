"""Shared constants, helpers, and quality gate builders for Autonomous QE workflows."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from backend.core import documents
from backend.core.errors import AllowanceError
from backend.maf.engine import RunContext
from backend.maf.workflows.shared import review_evidence, token_estimate, token_line
from backend.qe import carry
from backend.repos import git

DESIGN_BATCH = 4
DESIGN_REVIEW_BATCH = 8
CODE_REVIEW_BATCH = 8
GENERATE_BATCH = 8
PARTIAL_AFTER = 2  # earlier failures of a stage before it may end with a partial result


def _cell(text: str) -> str:
    """Format markdown table cell escaping pipes and extra whitespace."""
    return " ".join(str(text).split()).replace("|", "\\|")


def _number_cases(cases: list[dict]) -> None:
    """Assign deterministic case IDs sequentially."""
    for number, case in enumerate(cases, 1):
        case["id"] = f"TC-APP-{number:03d}"


def _files_of(requirements: list[dict]) -> list[str]:
    return list(dict.fromkeys(r["file"] for r in requirements if r.get("file")))


def _design_evidence(rc: RunContext, requirements: list[dict], cases: list[dict]) -> str:
    """Evidence for one review batch: only the requirements its cases cover, with quotes and citations."""
    wanted = [r for r in requirements if r["id"] in {c["requirement_id"] for c in cases}] or requirements
    return review_evidence(rc.project_id, wanted)


def settle(rc: RunContext, batches: list, outcomes: list, what: str) -> dict | None:
    """Finished batches are already saved. A failed one raises, so Retry repeats only it, until retries are used up."""
    for outcome in outcomes:
        if isinstance(outcome, BaseException) and not isinstance(outcome, Exception):
            raise outcome
    failed = [(batch, outcome) for batch, outcome in zip(batches, outcomes) if isinstance(outcome, Exception)]
    if not failed:
        return None
    if limit := next((o for _, o in failed if isinstance(o, AllowanceError)), None):
        raise limit
    for _, outcome in failed[1:]:
        rc.log(f"Another {what} batch failed: {getattr(outcome, 'code', type(outcome).__name__)} {str(outcome)[:200]}", kind="warning")
    if rc.earlier_failures() < PARTIAL_AFTER or len(failed) == len(batches):
        raise failed[0][1]
    missing = [item for batch, _ in failed for item in batch]
    rc.log(f"{what}: {len(failed)} of {len(batches)} batches kept failing. The result is PARTIAL and cannot be approved.", {"missing": missing}, "warning")
    return {"stage": rc.stage, "missing": missing, "codes": sorted({getattr(o, "code", "AQE-INT-001") for _, o in failed})}


def _doc_gate(gate: int, label: str, doc_key: str, summary: Callable[[dict], str], review_key: str | None = None, extras: Callable[[RunContext, dict], dict] | None = None):
    def build(rc: RunContext, state: dict):
        review = state.get(review_key) if review_key else None
        payload = {"documents": [state[doc_key]], "titles": [documents.get(state[doc_key])["title"]]}
        if gate == 1 and state.get("discovery_id"):
            payload = {"documents": [state["discovery_id"], *payload["documents"]], "titles": ["Discovery summary", *payload["titles"]]}
        if review:
            payload["confidence"] = review
        if extras:
            payload |= extras(rc, state)
        trace_line = ""
        payload["tokens"] = tokens = token_line(rc.run_id)
        if last := (state.get("trace") or {}).get("last"):
            payload["trace"] = last
            trace_line = " " + carry.summary(last)
        if state.get("partial"):
            payload["partial"] = state["partial"]
            return {"gate": gate, "title": f"Gate {gate} (PARTIAL): {label}", "summary": f"PARTIAL RESULT, not complete. Missing: {', '.join(state['partial']['missing'])}. {summary(state)}{trace_line} {tokens['text']}", "payload": payload}
        return {"gate": gate, "title": f"Gate {gate}: approve {label}", "summary": f"{summary(state)}{trace_line} {tokens['text']}", "payload": payload}

    return build


async def qe_commit(rc: RunContext, state: dict, answer: dict) -> dict:
    commit = await asyncio.to_thread(git.commit_all, Path(state["worktree"]), f"Add Agentic QE Platform generated tests\n\nApproved by {answer['by']} in run {rc.run_id}")
    return {"test_commit": commit}


def _gate3_extras(rc: RunContext, state: dict) -> dict:
    batches = -(-len(state["cases"]) // GENERATE_BATCH)
    extra = {"case_limit": state.get("case_limit"), "estimate": token_estimate(rc.run_id, "test-design-architect", batches, f"generation of {len(state['cases'])} cases in {batches} batches",
                                                                                f"average of the design agent's recorded calls, assuming a generation batch costs about one design call; reviews of the tests are not included")}
    if state.get("fixtures_doc"):
        extra |= {"documents": [state["cases_doc"], state["fixtures_doc"]], "titles": ["Test cases", "Test data"]}
    return extra


def _gate4_extras(rc: RunContext, state: dict) -> dict:
    return {"emit_unresolved": state.get("emit_unresolved", []), "validation": state.get("validation"), "estimate": token_estimate(rc.run_id, None, 4, "execution summary, up to two repair attempts, and the release review",
                                                                                          "upper bound: the average of every model call this run has recorded, times four calls")}


def _gate5_extras(rc: RunContext, state: dict) -> dict:
    return {"defect_records": state.get("defect_records", []), "execution_summary": state.get("execution_summary"), "failure_classes": state["summary"].get("failure_classes")}
