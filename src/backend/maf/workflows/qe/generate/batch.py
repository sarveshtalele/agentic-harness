"""Asking the test author for batches of cases, checking every file it sends, and building the suite from the batches."""
from __future__ import annotations

import asyncio
import json

from backend.core.errors import AllowanceError, AqeError, ModelSchemaError
from backend.maf.engine import part_key
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.common import GENERATE_BATCH, settle
from backend.maf.workflows.qe.generate.env import Env
from backend.maf.workflows.qe.generate.files import GeneratedFile, GeneratedSuite, _generated_file_problems
from backend.maf.workflows.shared import code_pack
from backend.qe import emit


async def generate_batch(env: Env, cases: list[dict]) -> tuple[dict[str, GeneratedFile], str, list[str]]:
    rc, state, worktree, a, known, files_of, feedback, notes, async_ok = env.rc, env.state, env.worktree, env.analysis, env.known, env.files_of, env.feedback, env.notes, env.async_ok
    batch_call = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
    code = code_pack(rc.project_id, worktree, list(dict.fromkeys(files_of[c["requirement_id"]] for c in cases if files_of.get(c["requirement_id"]))) or None, limit=30_000)
    wanted = {c["id"] for c in cases}
    under_test = list(dict.fromkeys(files_of[c["requirement_id"]] for c in cases if files_of.get(c["requirement_id"])))
    request = (f"Generate executable tests under tests/agentic_qe/ for these cases, one file per case. Send a file for every case.\nCASES:\n{json.dumps(cases)}\nDETECTED RUNNERS: {a['test_runners']}\n"
               f"Import only names you can see in this code. Name each test function with its case id, for example test_TC_APP_001_empty_input.\n"
               f"tests/agentic_qe/fixtures.json holds the shared datasets under \"datasets\" and, under \"cases\", one entry per case id with exactly two keys: \"data\" (the case's test data as text) "
               f"and \"uses\" (names of the shared datasets it uses). Load it with json and pathlib relative to __file__. Never define, copy or stub the code under test: import the repository's real module.\n"
               f"{notes}\n{emit.signatures(worktree, under_test)}{feedback}\n\nCODE:\n{code}")
    key = part_key("generate", sorted(wanted), state.get("feedback", ""))
    if saved := rc.kept(key):
        rc.log(f"Kept result reused for {len(wanted)} cases")
        return {p: GeneratedFile(**f) for p, f in saved["accepted"].items()}, saved["framework"], saved["errors"]
    accepted: dict[str, GeneratedFile] = {}
    errors: list[str] = []
    framework = ""
    for _ in range(3):
        try:
            suite = await batch_call.typed(request, GeneratedSuite)
        except AllowanceError:
            raise
        except AqeError as exc:
            if not accepted:
                raise
            errors = [str(exc)[:300]]
            break
        framework = suite.framework
        errors = []
        for item in suite.files:
            problems = _generated_file_problems(item, known, worktree, async_ok)
            if problems:
                errors.extend(problems)
                accepted.pop(item.path, None)
            else:
                accepted[item.path] = item
        covered = {cid for f in accepted.values() for cid in f.case_ids}
        missing = sorted(wanted - covered)
        if not errors and not missing:
            break
        request = "These generated test files were refused. Send corrected versions of only these files, with the same paths and case ids.\nPROBLEMS:\n" + "\n".join(errors[:40]) + (f"\nThese cases have no test yet, so send one file for each: {missing}" if missing else "") + f"\n\nCODE:\n{code}"
    rc.keep(key, {"accepted": {p: f.model_dump() for p, f in accepted.items()}, "framework": framework, "errors": errors})
    return accepted, framework, errors


async def synthesize(env: Env) -> tuple[GeneratedSuite, list[str], dict | None]:
    rc, state, known = env.rc, env.state, env.known
    batches = [state["cases"][i : i + GENERATE_BATCH] for i in range(0, len(state["cases"]), GENERATE_BATCH)]
    outcomes = await asyncio.gather(*(generate_batch(env, batch) for batch in batches), return_exceptions=True)
    partial = settle(rc, [[c["id"] for c in b] for b in batches], outcomes, "Generate")
    outcomes = [o for o in outcomes if not isinstance(o, BaseException)]
    accepted = {path: item for found, _, _ in outcomes for path, item in found.items()}
    errors = [problem for _, _, found in outcomes for problem in found]
    if lost := [c for c in state["cases"] if c["id"] not in {cid for f in accepted.values() for cid in f.case_ids}]:
        rc.log(f"{len(lost)} cases have no test yet. Asking once more in smaller batches", kind="warning")
        again = await asyncio.gather(*(generate_batch(env, lost[i : i + GENERATE_BATCH // 2]) for i in range(0, len(lost), GENERATE_BATCH // 2)), return_exceptions=True)
        for found in again:
            if isinstance(found, AllowanceError):
                raise found
            if isinstance(found, BaseException):
                errors.append(str(found)[:300])
            else:
                outcomes.append(found)
                accepted |= found[0]
                errors += found[2]
    if not accepted:
        raise ModelSchemaError(f"Generated tests failed checks: {errors}", action="Retry the stage. Each problem above names the file and the rule it broke.")
    suite = GeneratedSuite(framework=next((framework for _, framework, _ in outcomes if framework), ""), files=list(accepted.values()))
    missing = sorted(known - {cid for f in suite.files for cid in f.case_ids})
    if missing:
        rc.log(f"{len(missing)} of {len(known)} cases have no test: {missing[:30]}", {"problems": errors[:20]}, "warning")
    return suite, missing, partial
