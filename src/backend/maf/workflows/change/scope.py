"""Which files a change needs, and the deterministic checks that the requested work exists."""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from backend.core.security import PathEscape, safe_path
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.shared import _analysis
from backend.repos import git, scan, static_analysis


class FileSelection(BaseModel):
    files: list[str] = Field(min_length=1)


async def _select_files(rc: RunContext, state: dict, worktree: Path) -> list[str]:
    """Pick the files a change needs, so they travel in the message. Tool results can be lost between model rounds."""
    tree = scan.tree(worktree)
    tests = [f for f in tree if scan.TEST_NAME.search(f)][:6]
    if state.get("finding_files"):
        return [*state["finding_files"], *tests]
    if len(tree) <= 15:
        return tree
    picked = await AgentCall(rc.run_id, rc.project_id, "repo-intelligence-analyst", skills=()).typed(
        f"Choose up to 12 existing files needed to do this task, including one that shows how similar things are done and one related test.\nTASK:\n{state['spec'][:1500]}\n\nFILES:\n" + "\n".join(tree[:800]), FileSelection)
    chosen = [f for f in picked.files if f in tree]
    return chosen[:12] or static_analysis.rank_files_for_review(worktree, _analysis(rc.project_id), 12)


def spec_gaps(worktree: Path, state: dict) -> list[str]:
    """Deterministic completeness check. Old tests passing does not mean the requested work exists."""
    diff = git.diff(worktree)
    gaps = [f"function {name} named in the task is not in the diff" for name in sorted(set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+(?=\()", state["spec"]))) if name not in diff]
    changed = git.run(["diff", "--name-only"], cwd=worktree).splitlines()
    has_tests = any(scan.TEST_NAME.search(f) for f in scan.tree(worktree))
    if state.get("kind") == "feature" and has_tests and not any(scan.TEST_NAME.search(f) for f in changed):
        gaps.append("no test file was added or changed")
    gaps += [f"{name}, a file with a finding, was not changed" for name in state.get("finding_files", []) if name not in changed]
    return gaps


def safe_exists(root: Path, path: str) -> bool:
    try:
        return safe_path(root, path).is_file()
    except PathEscape:
        return False
