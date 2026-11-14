"""V1 at Gate 4: the coverage auditor (kind "code") checks each generated test against its case. A test it says MISSES is rewritten once, then audited again."""
from __future__ import annotations

import asyncio
import json

from backend.core.errors import AllowanceError
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.generate.env import Env
from backend.maf.workflows.qe.generate.files import GeneratedFile, GeneratedSuite
from backend.maf.workflows.qe.generate.repair import repair_static
from backend.maf.workflows.qe.generate.validate import _check, _write
from backend.maf.workflows.shared import review_evidence
from backend.qe import model, validity

AUDIT_BATCH = 8


def _shown(item: GeneratedFile, case_of: dict) -> dict:
    numbered = "\n".join(f"{n}: {line}" for n, line in enumerate(item.content.splitlines(), 1))
    return {"tc_id": item.case_ids[0], "case": case_of.get(item.case_ids[0], {}), "path": item.path, "test": numbered[:8_000]}


async def _audit(env: Env, items: list[GeneratedFile], case_of: dict) -> dict[str, dict]:
    """Verdicts by case id. A batch the auditor cannot answer is logged and left unaudited, never passed."""
    rc = env.rc
    chosen = {case_of[f.case_ids[0]]["requirement_id"] for f in items if f.case_ids[0] in case_of}

    async def ask(batch: list[GeneratedFile]) -> list[dict]:
        shown = [_shown(f, case_of) for f in batch]
        reply = await AgentCall(rc.run_id, rc.project_id, "coverage-auditor").typed(
            f"Audit these generated tests.\nTESTS:\n{json.dumps(shown)}\n\nREQUIREMENTS AND EVIDENCE:\n{review_evidence(rc.project_id, [r for r in env.state['requirements'] if r['id'] in chosen], env.worktree)}", model.AuditSet, attempts=2)
        ids = {x["tc_id"] for x in shown}
        return [v.model_dump() for v in reply.verdicts if v.id in ids]

    batches = [items[i : i + AUDIT_BATCH] for i in range(0, len(items), AUDIT_BATCH)]
    found: dict[str, dict] = {}
    for batch, outcome in zip(batches, await asyncio.gather(*(ask(b) for b in batches), return_exceptions=True)):
        if isinstance(outcome, AllowanceError) or (isinstance(outcome, BaseException) and not isinstance(outcome, Exception)):
            raise outcome
        if isinstance(outcome, Exception):
            rc.log(f"Code audit did not run for {len(batch)} tests: {str(outcome)[:200]}", {"cases": [f.case_ids[0] for f in batch]}, "warning")
            continue
        for v in outcome:
            found.setdefault(v["id"], v)
    return found


async def audit_tests(env: Env, suite: GeneratedSuite, case_of: dict) -> dict:
    """Returns {"verdicts": {case id: verdict}, "v1": {path: check}, "first": counts, "regenerated": n}. Changes `suite` and the worktree when it rewrites a test."""
    rc = env.rc
    verdicts = await _audit(env, suite.files, case_of)
    first = {k: sum(v["verdict"] == k for v in verdicts.values()) for k in ("COVERS", "PARTIAL", "MISSES")}
    missed = {f.path: (f.content, verdicts[f.case_ids[0]]["reason"]) for f in suite.files if verdicts.get(f.case_ids[0], {}).get("verdict") == "MISSES"}
    if missed:
        def check(item: GeneratedFile) -> list[str]:
            old = missed.get(item.path)
            if not old:
                return []  # only the tests the auditor flagged go back
            if item.content == old[0]:
                return [f"the coverage auditor says this test misses its case: {old[1]}. Exercise the behaviour the case's steps state and assert its expected result"]
            _write(env, [item])  # the rewrite must still pass V2b to V6
            return validity.problems(_check(env, item, case_of))

        await repair_static(env, suite, case_of, check, "coverage audit (V1)")
        _write(env, suite.files)
        changed = [f for f in suite.files if f.path in missed and f.content != missed[f.path][0]]
        if changed:
            verdicts |= await _audit(env, changed, case_of)
    v1: dict[str, dict] = {}
    for f in suite.files:
        v = verdicts.get(f.case_ids[0])
        v1[f.path] = ({"status": "NOT CHECKED", "message": "the coverage auditor gave no verdict"} if not v else
                      {"status": "FAIL", "message": f"the coverage auditor says this test misses its case: {v['reason']}. Exercise the behaviour the case's steps state and assert its expected result"} if v["verdict"] == "MISSES" else
                      {"status": "PASS", "message": f"{v['verdict']}: {v['reason']}"})
    now = {k: sum(v["verdict"] == k for v in verdicts.values()) for k in ("COVERS", "PARTIAL", "MISSES")}
    rc.log(f"Code audit: first {first}; {len(missed)} rewritten once; now {now}", {"first": first, "now": now}, "review")
    return {"verdicts": verdicts, "v1": v1, "first": first, "now": now, "regenerated": len(missed)}
