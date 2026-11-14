"""Static-check send-back, quarantine of unusable files, and writing the suite into the worktree."""
from __future__ import annotations

import asyncio
import json
import re

from backend.core.errors import AllowanceError
from backend.maf.runtime import AgentCall
from backend.maf.workflows.edits import Edit, apply_edits
from backend.maf.workflows.qe.generate.env import Env
from backend.maf.workflows.qe.generate.files import GeneratedFile, GeneratedSuite, _clean_code, _generated_file_problems
from backend.qe import emit, execution


async def repair_static(env: Env, suite: GeneratedSuite, case_of: dict, check=None, label: str = "static checks") -> list[dict]:
    """Sends each flagged file back to the author once. `check` (default: the static checks) returns a file's problems."""
    rc, worktree, known, files_of, notes, async_ok = env.rc, env.worktree, env.known, env.files_of, env.notes, env.async_ok
    static_findings = check or env.static_findings
    unresolved: list[dict] = []
    flagged = {i: found for i, item in enumerate(suite.files) if (found := static_findings(item))}
    if flagged:
        rc.log(f"{len(flagged)} generated tests failed the {label}. Each goes back alone, once", {"findings": {suite.files[i].path: found[:5] for i, found in flagged.items()}}, "warning")

    async def send_back(i: int, found: list[str]) -> GeneratedFile:
        old = suite.files[i]
        case = case_of.get(old.case_ids[0], {})
        under_test = files_of.get(case.get("requirement_id"))
        again = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
        result = await again.typed(f"Rewrite only this generated test file and fix every problem the {label} found. Send a suite with exactly this one file, with the same path and case id.\nCASE:\n{json.dumps(case)}\n"
                                   f"CURRENT FILE {old.path}:\n{old.content}\nPROBLEMS, each with the real signature:\n" + "\n".join(found[:20]) + f"\n{notes}\n{emit.signatures(worktree, [under_test] if under_test else [])}", GeneratedSuite, attempts=2)
        new = next((f for f in result.files if f.path == old.path and f.case_ids == old.case_ids), None)
        if new is None:
            raise ValueError("The agent did not send back the same file for the same case")
        if problems := _generated_file_problems(new, known, worktree, async_ok):
            raise ValueError("; ".join(problems[:3]))
        return new

    outcomes = await asyncio.gather(*(send_back(i, found) for i, found in flagged.items()), return_exceptions=True)
    for (i, found), outcome in zip(flagged.items(), outcomes):
        if isinstance(outcome, BaseException) and not isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, AllowanceError):
            raise outcome
        remaining = found
        if isinstance(outcome, Exception):
            rc.log(f"{suite.files[i].path} could not be sent back: {str(outcome)[:200]}", kind="warning")
        elif len(after := static_findings(outcome)) <= len(found):
            suite.files[i], remaining = outcome, after
        if remaining:
            unresolved.append({"path": suite.files[i].path, "case_id": suite.files[i].case_ids[0], "findings": remaining[:10]})
    if unresolved:
        rc.log(f"{len(unresolved)} tests still fail the static checks after one round. They stay, marked", {"unresolved": unresolved}, "warning")
    return unresolved


def quarantine_syntax(suite: GeneratedSuite, unresolved: list[dict]) -> None:
    valid_suite_files = []
    for f in suite.files:
        f.content = _clean_code(f.content)
        syn = execution.syntax_error(f.path, f.content)
        if syn:
            cid = f.case_ids[0] if f.case_ids else "unknown"
            norm_cid = re.sub(r"[^a-zA-Z0-9_]+", "_", cid)
            f.content = (
                f"# CASE_ID: {cid}\n"
                f"# Quarantined due to syntax error: {syn}\n"
                f"import pytest\n\n"
                f"@pytest.mark.skip(reason=\"Quarantined test: {syn}\")\n"
                f"def test_quarantined_{norm_cid}():\n"
                f"    pass\n"
            )
            unresolved.append({"path": f.path, "case_id": cid, "findings": [f"Syntax error: {syn}"]})
        valid_suite_files.append(f)
    suite.files = valid_suite_files


def write_suite(env: Env, suite: GeneratedSuite, unresolved: list[dict]) -> None:
    rc, state, worktree = env.rc, env.state, env.worktree
    edits = [Edit(path=f.path, action="create", content=f.content) for f in suite.files]
    if state.get("fixtures"):
        edits.append(Edit(path="tests/agentic_qe/fixtures.json", action="create", content=json.dumps(state["fixtures"], indent=2, ensure_ascii=False)))
    errors = apply_edits(worktree, edits)
    if errors:
        rc.log(f"{len(errors)} generated test edits had issues: {errors[:5]}", kind="warning")
        for err in errors:
            bad_path = err.split(":")[0].strip()
            for f in suite.files:
                if f.path == bad_path:
                    cid = f.case_ids[0] if f.case_ids else "unknown"
                    norm_cid = re.sub(r"[^a-zA-Z0-9_]+", "_", cid)
                    safe_stub = (
                        f"# CASE_ID: {cid}\n"
                        f"# Quarantined due to refusal: {err}\n"
                        f"import pytest\n\n"
                        f"@pytest.mark.skip(reason=\"Quarantined refusal: {err[:80]}\")\n"
                        f"def test_quarantined_{norm_cid}():\n"
                        f"    pass\n"
                    )
                    apply_edits(worktree, [Edit(path=f.path, action="create", content=safe_stub)])
                    unresolved.append({"path": f.path, "case_id": cid, "findings": [err]})