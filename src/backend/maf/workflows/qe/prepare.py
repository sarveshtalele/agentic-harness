"""QE Prepare Stage: Environment setup, dependency installation, and pytest-asyncio detection."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from backend.core.errors import ExecutionError
from backend.maf.engine import RunContext
from backend.maf.workflows.shared import _analysis
from backend.qe import emit, execution


async def qe_prepare(rc: RunContext, state: dict) -> dict:
    """Setup before the tests run: dependencies, pytest-asyncio for async tests, and environment facts."""
    worktree = Path(state["worktree"])
    try:
        if state.get("install_deps"):
            await asyncio.to_thread(execution.install_dependencies, worktree, _analysis(rc.project_id), rc.log)
        declared = emit.declared_dependencies(worktree)
        facts = await asyncio.to_thread(execution.environment_facts, worktree, declared)
        asyncs = await asyncio.to_thread(execution.async_test_files, worktree)
        if asyncs and not facts["pytest_asyncio"] and state.get("install_deps"):
            await asyncio.to_thread(execution.install_pytest_asyncio, worktree, rc.log)
            facts = await asyncio.to_thread(execution.environment_facts, worktree, declared)
    except (subprocess.SubprocessError, OSError) as exc:
        raise ExecutionError(f"Dependencies could not be installed: {type(exc).__name__}: {str(exc)[:200]}") from exc
    args = ["-o", "asyncio_mode=auto"] if asyncs and facts["pytest_asyncio"] else []
    if asyncs and not facts["pytest_asyncio"]:
        rc.log(f"{len(asyncs)} async tests need pytest-asyncio, which is not installed. They will fail and be classed as environment", {"files": asyncs[:20]}, "warning")
    rc.log(f"Prepared: httpx {facts['httpx'] or 'none'}, pytest-asyncio {'yes' if facts['pytest_asyncio'] else 'no'}, {len(asyncs)} async tests, {len(facts['rate_limiters'])} rate limiters", {"pytest_args": args, "rate_limiters": facts["rate_limiters"]})
    return {"env_facts": facts, "async_tests": asyncs, "pytest_args": args}
