"""What one generation stage knows: its worktree, the cases and requirements, and the facts about the target environment."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from backend.config import project_dir, repo_dir
from backend.maf.engine import RunContext
from backend.maf.workflows.shared import _analysis
from backend.qe import emit, execution
from backend.repos import git


@dataclass
class Env:
    rc: RunContext
    state: dict
    worktree: Path
    analysis: dict
    known: set
    files_of: dict
    feedback: str
    notes: str
    inventory: object
    allowed: object
    async_ok: bool
    facts: dict

    def static_findings(self, item):
        return emit.check(self.worktree, item.path, item.content, self.inventory, self.allowed)


async def prepare_worktree(rc: RunContext, state: dict) -> dict:
    root = repo_dir(rc.project_id)
    if not state.get("worktree"):
        if not root.exists():
            root.mkdir(parents=True)
            await asyncio.to_thread(git.init_snapshot, root, "Agentic QE Platform greenfield baseline")
            (root / ".gitkeep").write_text("", encoding="utf-8")
            await asyncio.to_thread(git.commit_all, root, "Agentic QE Platform greenfield baseline")
        worktree = project_dir(rc.project_id) / "worktrees" / rc.run_id
        worktree.parent.mkdir(parents=True, exist_ok=True)
        branch = f"atlas/qe-{rc.run_id[-6:]}"
        if not worktree.exists():
            await asyncio.to_thread(git.add_worktree, root, worktree, branch)
        state = {**state, "worktree": str(worktree), "branch": branch}
        rc.log(f"[SANDBOX_WORKTREE] Created isolated git worktree at {worktree} on branch {branch}")
    else:
        worktree = Path(state["worktree"])
        # a send-back regenerates the suite: this run's earlier, uncommitted files would otherwise run beside the new ones
        stale = await asyncio.to_thread(git.untracked, worktree, "tests/agentic_qe")
        for path in stale:
            path.unlink(missing_ok=True)
        rc.log(f"[SANDBOX_WORKTREE] Reusing verified git worktree at {worktree}; removed {len(stale)} uncommitted files of the earlier attempt")
    return state


async def load_env(rc: RunContext, state: dict, worktree: Path) -> Env:
    a = _analysis(rc.project_id)
    known = {c["id"] for c in state["cases"]}
    files_of = {r["id"]: r.get("file") for r in state["requirements"]}
    feedback = f"\nFEEDBACK:\n{state['feedback']}" if state.get("feedback") else ""
    install = bool(state.get("install_deps"))
    declared = emit.declared_dependencies(worktree)
    facts = await asyncio.to_thread(execution.environment_facts, worktree, declared)
    inventory = await asyncio.to_thread(emit.inventory, facts["python"])
    allowed = declared if install else frozenset()
    async_ok = bool(facts["pytest_asyncio"] or install)
    notes = execution.environment_notes(facts, install)
    rc.log(f"Environment: httpx {facts['httpx'] or 'not installed'}, pytest-asyncio {'yes' if facts['pytest_asyncio'] else 'no'}, {len(facts['rate_limiters'])} rate limiters" + ("" if inventory else ". The installed packages could not be read, so the third-party import check is skipped"), facts)
    return Env(rc, state, worktree, a, known, files_of, feedback, notes, inventory, allowed, async_ok, facts)
