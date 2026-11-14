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
from backend.maf.workflows.shared import review_cases, review_with_send_back
from backend.qe import confidence, model, plugin_bridge


async def qe_design(rc: RunContext, state: dict) -> dict:
    import backend.maf.workflows.qe as qe_mod
    effective_max_cases = getattr(qe_mod, "MAX_CASES", MAX_CASES)
    call = AgentCall(rc.run_id, rc.project_id, "test-design-architect", skills=("designing-test-cases",))
    feedback = f"\nFEEDBACK:\n{state['feedback']}" if state.get("feedback") else ""
    root = repo_dir(rc.project_id)
    source = root if root.exists() else None
    budget = model.case_quota(state["requirements"], effective_max_cases)
    quota = budget["quota"]
    dropped: list[dict] = []
    rc.log(budget["message"], budget, "warning" if budget["left_out_requirements"] or budget["p0_over_limit"] else "log")

    def asked_for(requirements: list[dict]) -> str:
        return ("\nCASE QUOTA, at most this many cases for each requirement (for 4: 1 Positive, 2 Negative, then 1 Exception only when the requirement states error behaviour, "
                "else a third Negative; with fewer, the Positive case first). Test data must be of the requirement's input_type:\n") + ", ".join(f"{r['id']}: {quota.get(r['id'], 0)}" for r in requirements)

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
        found, over = model.apply_quota(await design(requirements), quota, requirements)

        async def revise_case(i: int, record: dict, calls: list) -> str:
            old = found[i]
            again = AgentCall(rc.run_id, rc.project_id, "test-design-architect", skills=("designing-test-cases",))
            calls.append(again)
            owner = [r for r in requirements if r["id"] == old["requirement_id"]] or requirements
            result = await again.typed(f"Rewrite only this one test case and fix every flaw the independent reviewer found. Keep its type, except that an Exception case for a requirement that states no error behaviour becomes a Negative case. Send one case.\nREQUIREMENT:\n{json.dumps(owner)}\nCASE:\n{json.dumps(old)}\nFLAWS AND FIXES:\n{confidence.flaw_lines(record)}\nPLAN:\n{json.dumps(state['plan'])}", model.CaseSet, attempts=2)
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
    # batches number their cases separately, so ids are assigned here
    _number_cases(cases)
    checks = lambda found: model.coverage_gaps(state["requirements"], found) + [why for _, why in model.case_problems(state["requirements"], found)]
    gaps, dupes = checks(cases), model.duplicate_scenarios(cases)
    if gaps or dupes:
        rc.log(f"Design checks found gaps {gaps} and duplicates {dupes}; revising", kind="warning")
        affected = {g.split(":")[0] for g in gaps} | {c["requirement_id"] for c in cases if c["id"] in dupes}
        missing = set(partial["missing"]) if partial else set()  # a partial result is not designed again here
        wanted = [r for r in designed if r["id"] in affected - missing] or ([] if partial else designed)
        if wanted:
            revised, over = model.apply_quota(await design(wanted, f"\n\nThese cases failed checks. Gaps: {gaps}. Duplicates: {dupes}. Return a full corrected set for these requirements, within the case quota."), quota, wanted)
            dropped += over
            fresh, spent = await review_cases(rc, "design", "design cases", [(f"C{n}", json.dumps(c)) for n, c in enumerate(revised, 1)], lambda keys: _design_evidence(rc, wanted, [revised[int(k[1:]) - 1] for k in keys]), source, DESIGN_REVIEW_BATCH)
            tokens["review"] += spent
            tokens["total"] += spent
            pairs = [p for p in pairs if p[0]["requirement_id"] not in {r["id"] for r in wanted}] + list(zip(revised, fresh))
            cases = [case for case, _ in pairs]
        refused = model.case_problems(state["requirements"], cases)  # still of the wrong type after the revision, so the case is refused
        pairs = [p for p in pairs if not any(p[0] is case for case, _ in refused)]
        cases = [case for case, _ in pairs]
        gaps = model.coverage_gaps(state["requirements"], cases) + [f"refused {why}" for _, why in refused]
    _number_cases(cases)
    records = {case["id"]: {**record, "tc_id": case["id"]} for case, record in pairs}
    # final safety check: after the quota nothing should be cut here, and if something is, it is reported
    cases, cut = model.limit_cases(cases, state["requirements"], max(effective_max_cases, budget["planned"]))
    case_limit = {**cut, "limit": effective_max_cases, "quota": quota, "planned": budget["planned"], "left_out_requirements": budget["left_out_requirements"], "p0_over_limit": budget["p0_over_limit"],
                  "dropped_over_quota": [{k: c.get(k) for k in ("requirement_id", "type", "scenario")} for c in dropped]}
    case_limit["requirements_without_cases"] = [r["id"] for r in state["requirements"] if r["id"] not in {c["requirement_id"] for c in cases}]
    case_limit["left_out_count"] = cut["left_out_count"] + len(dropped)
    case_limit["message"] = budget["message"] + (f"; {len(dropped)} excess cases dropped before review" if dropped else "") + (f"; {cut['left_out_count']} more cut by the final check" if cut["left_out_count"] else "")
    case_limit["notice"] = bool(case_limit["left_out_count"] or budget["left_out_requirements"] or budget["p0_over_limit"])
    if case_limit["notice"]:
        rc.log(case_limit["message"], case_limit, "warning")
    cases_review = confidence.summarise([records[c["id"]] for c in cases], tokens)
    rc.log(f"Design review: {cases_review['counts']}, {tokens['total']} tokens", {"tokens": tokens}, "review")
    columns = "| TC ID | Requirement | Scenario | Type | Level | Precondition | Test Data | Steps | Expected Result | Oracle | Priority |\n|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = columns + "\n".join(f"| {c['id']} | {c['requirement_id']} | {_cell(c['scenario'])} | {c['type']} | {c['level']} | {_cell(c['precondition'])} | {_cell(c['test_data'])} | {_cell(' '.join(f'{i + 1}. {s}' for i, s in enumerate(c['steps'])))} | {_cell(c['expected_result'])} | {c['oracle']} | {c['priority']} |" for c in cases)
    if case_limit["notice"]:
        body = f"> {case_limit['message']}. Requirements with no case now: {', '.join(case_limit['requirements_without_cases']) or 'none'}\n\n" + body
    if partial:
        body = f"> PARTIAL RESULT. No cases yet for: {', '.join(partial['missing'])}\n\n" + body
    doc = documents.create(rc.project_id, "test_cases", f"Deterministic Test Cases & Scenario Matrix (PARTIAL, {len(partial['missing'])} requirements missing)" if partial else "Deterministic Test Cases & Scenario Matrix", body, "agent:test-design-architect", data=cases, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    rc.log(f"{len(cases)} cases designed; {len(gaps)} remaining gaps", {"gaps": gaps}, "artifact")
    design_audit = await _plugin_design(rc, state, cases, records)
    return {"cases": cases, "cases_doc": doc["id"], "design_gaps": gaps, "case_limit": case_limit, "cases_review": cases_review, "partial": partial,
            "design_audit": design_audit}


AUDIT_BATCH = 10


async def _plugin_design(rc: RunContext, state: dict, cases: list[dict], records: dict[str, dict]) -> dict:
    """The plugin's Gate 3 inputs: test_cases.json, the confidence reviewer's records, and the coverage auditor's verdicts."""
    if state["mode"] != "brownfield" or not cases:
        return {"ok": None, "error": "greenfield or no cases: the plugin's design files are not written"}
    app = plugin_bridge.app_name(rc.project_id)
    links = plugin_bridge.cases_file(cases, state["plan"])
    plugin_bridge.write(rc.project_id, app, "04-design/test_cases.json", links)
    reviewed = [records[c["id"]] for c in cases if c["id"] in records and records[c["id"]].get("verdict") != "NOT RUN"]
    plugin_bridge.write(rc.project_id, app, "04-design/confidence.json", plugin_bridge.recorded("confidence-reviewer", f"{rc.run_id}:design", "design", "items", reviewed))
    scenarios = json.dumps(plugin_bridge.plan_file(state["plan"])["scenarios"])

    async def audit(batch: list[dict]) -> list[dict]:
        call = AgentCall(rc.run_id, rc.project_id, "coverage-auditor")
        given = [x for x in links["cases"] if x["tc_id"] in {c["id"] for c in batch}]
        reply = await call.typed(f"Audit these designed cases.\nPLAN SCENARIOS:\n{scenarios}\n\nCASES:\n{json.dumps(given)}\n\nREQUIREMENTS AND EVIDENCE:\n{_design_evidence(rc, state['requirements'], batch)[:30_000]}", model.AuditSet, attempts=2)
        ids = {x["tc_id"] for x in given}
        return [v.model_dump() for v in reply.verdicts if v.id in ids]  # an id it was not given is not a verdict

    batches = [cases[i : i + AUDIT_BATCH] for i in range(0, len(cases), AUDIT_BATCH)]
    outcomes = await asyncio.gather(*(audit(b) for b in batches), return_exceptions=True)
    verdicts: dict[str, dict] = {}
    for batch, outcome in zip(batches, outcomes):
        if isinstance(outcome, AllowanceError) or (isinstance(outcome, BaseException) and not isinstance(outcome, Exception)):
            raise outcome
        if isinstance(outcome, Exception):
            rc.log(f"Coverage audit did not run for {len(batch)} cases: {str(outcome)[:200]}", {"cases": [c["id"] for c in batch]}, "warning")
            continue
        for v in outcome:
            verdicts.setdefault(v["id"], v)
    plugin_bridge.write(rc.project_id, app, "04-design/audit.json", plugin_bridge.recorded("coverage-auditor", f"{rc.run_id}:design", "design", "verdicts", list(verdicts.values())))
    counts = {k: sum(v["verdict"] == k for v in verdicts.values()) for k in ("COVERS", "PARTIAL", "MISSES")}
    result = {"app": app, "reviewed": len(reviewed), "audited": len(verdicts), "counts": counts, "unaudited": [c["id"] for c in cases if c["id"] not in verdicts]}
    rc.log(f"Coverage audit: {counts}; {len(result['unaudited'])} cases not audited", result, "review")
    return result
