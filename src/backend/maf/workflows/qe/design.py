"""QE Design Stage: Test Design Architect test case synthesis with confidence reviews."""
from __future__ import annotations

import asyncio
import json
from backend.config import MAX_CASES, repo_dir
from backend.core import documents
from backend.core.errors import AllowanceError
from backend.maf.engine import RunContext, part_key
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.common import (
    DESIGN_BATCH,
    DESIGN_REVIEW_BATCH,
    _cell,
    _design_evidence,
    _number_cases,
    settle,
)
from backend.maf.workflows.shared import review_with_send_back
from backend.qe import confidence, model


async def qe_design(rc: RunContext, state: dict) -> dict:
    call = AgentCall(rc.run_id, rc.project_id, "test-design-architect", skills=("designing-test-cases",))
    feedback = f"\nFEEDBACK:\n{state['feedback']}" if state.get("feedback") else ""
    root = repo_dir(rc.project_id)
    source = root if root.exists() else None
    budget = model.case_quota(state["requirements"], MAX_CASES)
    quota = budget["quota"]
    dropped: list[dict] = []
    rc.log(budget["message"], budget, "warning" if budget["left_out_requirements"] or budget["p0_over_limit"] else "log")

    def asked_for(requirements: list[dict]) -> str:
        return "\nCASE QUOTA, at most this many cases for each requirement (for 4: 1 Positive, 2 Negative, 1 Exception; with fewer, the Positive case first):\n" + ", ".join(f"{r['id']}: {quota.get(r['id'], 0)}" for r in requirements)

    async def design(requirements: list[dict], note: str = "") -> list[dict]:
        batch_call = AgentCall(rc.run_id, rc.project_id, "test-design-architect", skills=("designing-test-cases",))
        try:
            result = await batch_call.typed(f"Design test cases for only these requirements.\nREQUIREMENTS:\n{json.dumps(requirements)}{asked_for(requirements)}\nPLAN:\n{json.dumps(state['plan'])}{feedback}{note}", model.CaseSet, attempts=2)
        except AllowanceError:
            raise
        except RuntimeError as exc:
            if len(requirements) < 2:
                raise
            rc.log(f"Splitting a design batch of {len(requirements)} requirements: {str(exc)[:160]}", kind="warning")
            half = len(requirements) // 2
            parts = await asyncio.gather(design(requirements[:half], note), design(requirements[half:], note))
            return [case for part in parts for case in part]
        return [c.model_dump() for c in result.cases]

    async def design_and_review(requirements: list[dict]) -> tuple[list[dict], list[dict], dict, list[dict]]:
        found, over = model.apply_quota(await design(requirements), quota)

        async def revise_case(i: int, record: dict, calls: list) -> str:
            old = found[i]
            again = AgentCall(rc.run_id, rc.project_id, "test-design-architect", skills=("designing-test-cases",))
            calls.append(again)
            owner = [r for r in requirements if r["id"] == old["requirement_id"]] or requirements
            result = await again.typed(f"Rewrite only this one test case, keeping its type, and fix every flaw the independent reviewer found. Send one case.\nREQUIREMENT:\n{json.dumps(owner)}\nCASE:\n{json.dumps(old)}\nFLAWS AND FIXES:\n{confidence.flaw_lines(record)}\nPLAN:\n{json.dumps(state['plan'])}", model.CaseSet, attempts=2)
            found[i] = {**result.cases[0].model_dump(), "requirement_id": old["requirement_id"]}
            return json.dumps(found[i])

        records, tokens = await review_with_send_back(rc, "design", "design cases", [(f"C{n}", json.dumps(c)) for n, c in enumerate(found, 1)],
                                                      lambda indexes: _design_evidence(rc, requirements, [found[i] for i in indexes]), source, revise_case, DESIGN_REVIEW_BATCH)
        return found, records, tokens, over

    designed = [r for r in state["requirements"] if r["id"] in quota]
    batches = [designed[i : i + DESIGN_BATCH] for i in range(0, len(designed), DESIGN_BATCH)]

    async def finished_or_new(batch: list[dict]) -> tuple[list[dict], list[dict], dict, list[dict]]:
        key = part_key("design", [r["id"] for r in batch], state.get("feedback", ""), [quota[r["id"]] for r in batch])
        if (saved := rc.kept(key)) and saved.get("records"):
            rc.log(f"Kept result reused for {len(batch)} requirements: {batch[0]['id']} to {batch[-1]['id']}")
            return saved["cases"], saved["records"], saved["tokens"], saved.get("dropped", [])
        found, records, tokens, over = await design_and_review(batch)
        rc.keep(key, {"cases": found, "records": records, "tokens": tokens, "dropped": over})
        return found, records, tokens, over

    outcomes = await asyncio.gather(*(finished_or_new(b) for b in batches), return_exceptions=True)
    partial = settle(rc, [[r["id"] for r in b] for b in batches], outcomes, "Design")
    done = [o for o in outcomes if not isinstance(o, BaseException)]
    pairs = [(case, record) for found, records, _, _ in done for case, record in zip(found, records)]
    dropped += [c for _, _, _, over in done for c in over]
    tokens = {k: sum(t.get(k, 0) for _, _, t, _ in done) for k in ("review", "revise", "total")}
    cases = [case for case, _ in pairs]
    _number_cases(cases)
    gaps, dupes = model.coverage_gaps(state["requirements"], cases), model.duplicate_scenarios(cases)
    if gaps or dupes:
        rc.log(f"Design checks found gaps {gaps} and duplicates {dupes}; revising", kind="warning")
        fix_prompt = f"Design cases to close these gaps: {gaps}. Deduplicate these scenarios: {dupes}.\nREQUIREMENTS:\n{json.dumps(state['requirements'])}\nEXISTING CASES:\n{json.dumps(cases)}"
        try:
            extra = await call.typed(fix_prompt, model.CaseSet, attempts=2)
            cases, _ = model.apply_quota(cases + [c.model_dump() for c in extra.cases], quota)
            _number_cases(cases)
        except Exception as exc:
            rc.log(f"Could not revise design gaps: {str(exc)[:200]}", kind="warning")
    cases_review = confidence.summarise([record for _, record in pairs], tokens)
    rc.log(f"Design review: {cases_review['counts']}, {cases_review['tokens']['total']} tokens")
    gaps = model.coverage_gaps(state["requirements"], cases)
    if dropped:
        rc.log(f"{len(dropped)} cases over quota were dropped before review: {', '.join(d.get('title', '') for d in dropped[:6])}")
    body = "| ID | Requirement | Scenario | Type | Level | Priority |\n|---|---|---|---|---|---|\n" + "\n".join(
        f"| {c['id']} | {c['requirement_id']} | {_cell(c['scenario'])} | {c['type']} | {c['level']} | {c['priority']} |" for c in cases)
    if partial:
        body = f"> PARTIAL RESULT. No cases yet for: {', '.join(partial['missing'])}\n\n" + body
    doc = documents.create(rc.project_id, "test_cases", "Deterministic Test Cases & Scenario Matrix (PARTIAL)" if partial else "Deterministic Test Cases & Scenario Matrix", body, "agent:test-design-architect", data=cases, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    rc.log(f"{len(cases)} cases designed; {len(gaps)} remaining gaps", kind="artifact")
    return {"cases": cases, "cases_doc": doc["id"], "design_gaps": gaps, "case_limit": budget, "cases_review": cases_review, "partial": partial}
