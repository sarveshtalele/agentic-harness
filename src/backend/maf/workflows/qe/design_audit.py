"""Gate 3 inputs for the agentic-qe plugin: cases, the confidence reviewer's records and the coverage auditor's verdicts,
with one redesign of the cases the auditor says miss their scenario."""
from __future__ import annotations

import asyncio
import json

from backend.core.errors import AllowanceError
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.common import DESIGN_REVIEW_BATCH, _design_evidence
from backend.maf.workflows.shared import review_cases
from backend.qe import model, oracle, plugin_bridge

AUDIT_BATCH = 10


async def plugin_design(rc: RunContext, state: dict, cases: list[dict], records: dict[str, dict], source, known: dict[str, dict] | None = None) -> dict:
    """The plugin's Gate 3 inputs: test_cases.json, the confidence reviewer's records, and the coverage auditor's verdicts.

    First code refuses a case whose expected result names a value its requirement's quote and the code near the citation do not contain (V2);
    it is redesigned once, and one that still does is marked REJECT. The two reviewers must agree: a case the auditor says MISSES its scenario is redesigned once from the auditor's reason,
    reviewed and audited again; one that still misses is marked REJECT, so a person must give a reason to approve it.
    `known` holds the verdicts of cases kept from the earlier design: they are neither audited nor redesigned again.
    Changes `cases` and `records` in place; the result carries `verdicts` (the caller keeps them for a send-back).
    """
    if not cases or not any(r.get("file") for r in state["requirements"]):
        return {"ok": None, "error": "no cases, or requirements that cite no saved text: the plugin's design files are not written"}
    app = plugin_bridge.app_name(rc.project_id)
    scenarios = json.dumps(plugin_bridge.plan_file(state["plan"])["scenarios"])

    async def audit(batch: list[dict]) -> list[dict]:
        call = AgentCall(rc.run_id, rc.project_id, "coverage-auditor")
        given = plugin_bridge.cases_file(batch, state["plan"])["cases"]
        reply = await call.typed(f"Audit these designed cases.\nPLAN SCENARIOS:\n{scenarios}\n\nCASES:\n{json.dumps(given)}\n\nREQUIREMENTS AND EVIDENCE:\n{_design_evidence(rc, state['requirements'], batch)[:30_000]}", model.AuditSet, attempts=2)
        ids = {x["tc_id"] for x in given}
        return [v.model_dump() for v in reply.verdicts if v.id in ids]  # an id it was not given is not a verdict

    async def audit_all(group: list[dict]) -> dict[str, dict]:
        batches = [group[i : i + AUDIT_BATCH] for i in range(0, len(group), AUDIT_BATCH)]
        found: dict[str, dict] = {}
        for batch, outcome in zip(batches, await asyncio.gather(*(audit(b) for b in batches), return_exceptions=True)):
            if isinstance(outcome, AllowanceError) or (isinstance(outcome, BaseException) and not isinstance(outcome, Exception)):
                raise outcome
            if isinstance(outcome, Exception):
                rc.log(f"Coverage audit did not run for {len(batch)} cases: {str(outcome)[:200]}", {"cases": [c["id"] for c in batch]}, "warning")
                continue
            for v in outcome:
                found.setdefault(v["id"], v)
        return found

    async def redesign(case: dict, why: str) -> dict:
        call = AgentCall(rc.run_id, rc.project_id, "test-design-architect", skills=("designing-test-cases",))
        owner = [r for r in state["requirements"] if r["id"] == case["requirement_id"]]
        result = await call.typed(f"Rewrite only this one test case so it exercises the plan scenario it is linked to, at its level, with an expected result that would fail if the behaviour broke. Keep its type and level. Send one case.\nTHE REVIEW SAID: {why}\nREQUIREMENT:\n{json.dumps(owner)}\nCASE:\n{json.dumps(case)}\nPLAN SCENARIOS:\n{scenarios}", model.CaseSet, attempts=2)
        return {**result.cases[0].model_dump(), "id": case["id"], "requirement_id": case["requirement_id"]}

    async def redo(fixes: dict[int, str]) -> None:
        """Redesign each named case once, review the new ones, and keep their records."""
        fixed = await asyncio.gather(*(redesign(cases[i], why) for i, why in fixes.items()), return_exceptions=True)
        changed = []
        for i, new in zip(fixes, fixed):
            if isinstance(new, AllowanceError):
                raise new
            if isinstance(new, Exception):
                rc.log(f"Redesign of {cases[i]['id']} failed: {str(new)[:160]}", kind="warning")
                continue
            cases[i] = new
            changed.append(new)
        if changed:
            fresh, _ = await review_cases(rc, "design", "design cases", [(c["id"], json.dumps(c)) for c in changed], lambda keys: _design_evidence(rc, state["requirements"], changed), source, DESIGN_REVIEW_BATCH)
            records.update({c["id"]: {**r, "tc_id": c["id"]} for c, r in zip(changed, fresh)})
            verdicts.update(await audit_all(changed))

    verdicts: dict[str, dict] = dict(known or {})
    fresh = {c["id"] for c in cases} - set(verdicts)
    refused = oracle.problems([c for c in cases if c["id"] in fresh], state["requirements"], source)  # V2, before the audit, so the auditor sees the redesigned cases
    if refused:
        rc.log(f"Oracle check refused {len(refused)} cases: an expected value is not in the quote or the code. Redesigning once", refused, "warning")
        await redo({i: refused[c["id"]] for i, c in enumerate(cases) if c["id"] in refused})
    verdicts |= await audit_all([c for c in cases if c["id"] in fresh and c["id"] not in verdicts])
    first = {k: sum(v["verdict"] == k for v in verdicts.values()) for k in ("COVERS", "PARTIAL", "MISSES")}
    misses = [i for i, c in enumerate(cases) if c["id"] in fresh and verdicts.get(c["id"], {}).get("verdict") == "MISSES"]
    if misses:
        await redo({i: verdicts[cases[i]["id"]]["reason"] for i in misses})
    for c in (c for c in cases if c["id"] in fresh):  # a case still refused by the oracle check: a person must answer
        if why := oracle.problems([c], state["requirements"], source).get(c["id"]):
            rec = records.get(c["id"])
            if rec:
                records[c["id"]] = {**rec, "verdict": "REJECT", "low": True, "low_reason": "the expected result names a value the requirement and code do not contain",
                                    "flaws": [*rec.get("flaws", []), {"dimension": "oracle", "evidence": "oracle check", "fix": why}]}
    for c in (c for c in cases if c["id"] in fresh):  # still missing after one redesign: the reviewers' disagreement becomes a REJECT a person must answer
        v = verdicts.get(c["id"])
        if v and v["verdict"] == "MISSES" and c["id"] in records:
            rec = records[c["id"]]
            records[c["id"]] = {**rec, "verdict": "REJECT", "low": True, "low_reason": "the coverage auditor says this case misses its scenario",
                                "flaws": [*rec.get("flaws", []), {"dimension": "coverage", "evidence": "coverage-auditor", "fix": v["reason"]}]}
    plugin_bridge.write(rc.project_id, app, "04-design/test_cases.json", plugin_bridge.cases_file(cases, state["plan"]))
    reviewed = [records[c["id"]] for c in cases if c["id"] in records and records[c["id"]].get("verdict") != "NOT RUN"]
    plugin_bridge.write(rc.project_id, app, "04-design/confidence.json", plugin_bridge.recorded("confidence-reviewer", f"{rc.run_id}:design", "design", "items", reviewed))
    plugin_bridge.write(rc.project_id, app, "04-design/audit.json", plugin_bridge.recorded("coverage-auditor", f"{rc.run_id}:design", "design", "verdicts", [verdicts[c["id"]] for c in cases if c["id"] in verdicts]))
    counts = {k: sum(verdicts.get(c["id"], {}).get("verdict") == k for c in cases) for k in ("COVERS", "PARTIAL", "MISSES")}
    result = {"app": app, "reviewed": len(reviewed), "audited": sum(c["id"] in verdicts for c in cases), "counts": counts, "first_audit": first,
              "redesigned": len(misses), "oracle_refused": len(refused), "oracle_still": [c["id"] for c in cases if c["id"] in fresh and oracle.problems([c], state["requirements"], source)], "verdicts": verdicts, "unaudited": [c["id"] for c in cases if c["id"] not in verdicts]}
    rc.log(f"Coverage audit: first {first}; {len(misses)} redesigned; now {counts}", {k: v for k, v in result.items() if k != "verdicts"}, "review")
    return result
