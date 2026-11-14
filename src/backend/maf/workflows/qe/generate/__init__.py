"""QE Test Generation Stage: Synthesizing executable deterministic test suites in isolated sandbox worktrees."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.maf.engine import RunContext
from backend.maf.workflows.shared import _analysis
from backend.qe import execution
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.generate.batch import synthesize
from backend.maf.workflows.qe.generate.env import load_env, prepare_worktree
from backend.maf.workflows.qe.generate.files import GeneratedFile, GeneratedSuite, _clean_code, _generated_file_problems
from backend.maf.workflows.qe.generate.repair import quarantine_syntax, repair_static, write_suite
from backend.maf.workflows.qe.generate.review import review_and_save
from backend.maf.workflows.qe.generate.validate import finish, validate


async def qe_generate(rc: RunContext, state: dict) -> dict:
    state = await prepare_worktree(rc, state)
    worktree = Path(state["worktree"])
    rc.log(f"[TEST_SYNTHESIS_STARTED] Synthesizing deterministic test suite for {len(state['cases'])} cases in sandbox...")
    call = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
    if state.get("install_deps"):  # the validity checks collect in the repository's own environment, so it must exist before them
        await asyncio.to_thread(execution.install_dependencies, worktree, _analysis(rc.project_id), rc.log)
    env = await load_env(rc, state, worktree)
    suite, missing, partial = await synthesize(env)
    case_of = {c["id"]: c for c in state["cases"]}
    unresolved = await repair_static(env, suite, case_of)
    quarantine_syntax(suite, unresolved)
    write_suite(env, suite, unresolved)
    checked = await validate(env, suite, case_of)
    update = await review_and_save(env, suite, unresolved, case_of, call, missing, partial)
    return update | {"validation": await finish(env, suite, case_of, checked)}


__all__ = ["GeneratedFile", "GeneratedSuite", "_clean_code", "_generated_file_problems", "qe_generate"]
