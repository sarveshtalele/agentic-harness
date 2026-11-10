"""The run_tests agent tool: the project's own tests, in its sandbox copy, with counts computed from JUnit."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

from agent_framework import tool
from pydantic import Field

from backend.config import project_dir, repo_dir
from backend.core.security import PathEscape, safe_path
from backend.qe import execution
from backend.repos import ingest, sandbox


def _run(project_id: str, target: str) -> dict:
    if not (repo_dir(project_id) / ".git").exists():
        return {"verdict": "INCONCLUSIVE", "reason": "No repository is connected to this project, so there is nothing to test"}
    source = ingest.get(project_id)
    runners = execution.choose_runners(source["analysis"] if source else {})
    if not runners:
        return {"verdict": "INCONCLUSIVE", "reason": "No registered test runner (pytest, vitest, jest, playwright) found for this repository"}
    # ponytail: the sandbox is cloned once and reused; a re-synced repository reaches it on the next workflow run
    work = sandbox.initialize_sandbox(project_id)
    try:
        safe_path(work, target or ".")
    except PathEscape:
        return {"verdict": "INCONCLUSIVE", "reason": f"Target {target!r} is outside the repository"}
    results = [execution.run_suite(r, work, target or ".", project_dir(project_id) / "harness-results", timeout=600) for r in runners]
    return {"results": [{**{k: r[k] for k in ("runner", "target", "verdict", "reason", "total", "passed", "failed", "skipped", "exit_code")},
                         "failures": [{"test": f"{c['classname']}::{c['name']}", "message": c["message"][:400]} for c in r["cases"] if c["status"] == "failed"][:15]}
                        for r in results]}


def build(project_id: str, thread_id: str, start_run):
    @tool(name="run_tests", description="Run this project's own test suite in its isolated sandbox copy with the repository's test runner. "
                                        "Returns pass and fail counts read from the runner's JUnit report, and the failing tests.")
    async def run_tests(target: Annotated[str, Field(description="Test folder or file relative to the repository root, or '.' for everything")] = ".") -> str:
        return json.dumps(await asyncio.to_thread(_run, project_id, target))

    return run_tests
