"""Each project's sandbox setup: ensure, initialize, info, history."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from backend.config import project_dir, repo_dir, sandbox_dir
from backend.db import db, row
from backend.repos import git, github
from backend.core.errors import RepoError


def complete_history(project_id: str) -> bool:
    """Older clones were shallow. Returns True when missing history was fetched."""
    repo = repo_dir(project_id)
    if not repo.exists() or not git.is_shallow(repo):
        return False
    with db() as con:
        source = row(con.execute("SELECT credential_id FROM repo_sources WHERE project_id=?", (project_id,)))
    git.run(["fetch", "--unshallow", "--no-tags", "origin"], cwd=repo, token=github.token_for(source["credential_id"]) if source else None, timeout=600)
    return True


def ensure_sandbox(project_id: str) -> Path:
    """The project's repository folder. Without a connected repository this refuses: nothing is invented in its place."""
    repo = repo_dir(project_id)
    if not (repo / ".git").exists():
        raise RepoError("No repository is connected to this project. Connect one on the Repository page first")
    return repo


def initialize_sandbox(project_id: str, force: bool = False) -> Path:
    """Initialize dedicated sandbox directory in data/projects/<project_id>/sandbox.
    Clones or links from the project's repo folder so tests and changes run in isolation.
    """
    root = project_dir(project_id)
    repo = ensure_sandbox(project_id)
    sbox = sandbox_dir(project_id)
    root.mkdir(parents=True, exist_ok=True)

    if sbox.exists() and force:
        shutil.rmtree(sbox, ignore_errors=True)

    if not sbox.exists() or not (sbox / ".git").exists():
        git.run(["clone", str(repo), str(sbox)])

        # Configure local git user
        git.run(["config", "user.name", "Agentic QE Platform"], cwd=sbox)
        git.run(["config", "user.email", "agentic-qe@localhost"], cwd=sbox)

    # Share root node_modules for clean tooling execution (npx, tsc, vitest) if present
    from backend.config import ROOT
    root_nm = ROOT / "node_modules"
    if root_nm.exists():
        for target in [sbox / "node_modules", sbox / "frontend" / "node_modules"]:
            if target.parent.exists() and not target.exists():
                try:
                    os.symlink(root_nm, target)
                except Exception:
                    pass

    return sbox


def info(project_id: str) -> dict:
    root, repo, sbox = project_dir(project_id), repo_dir(project_id), sandbox_dir(project_id)
    worktrees = root / "worktrees"
    runs = [p.name for p in worktrees.iterdir() if p.is_dir() and p.name.startswith("run_") and not p.name.endswith(("-results", "-baseline"))] if worktrees.exists() else []
    size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink() and ".venv" not in p.parts) if root.exists() else 0
    has_repo = repo.exists() and (repo / ".git").exists()
    has_sandbox = sbox.exists() and (sbox / ".git").exists()
    active_git = sbox if has_sandbox else (repo if has_repo else None)
    current_branch = git.run(["branch", "--show-current"], cwd=active_git, check=False) if active_git else ""

    return {
        "path": str(root),
        "repo_path": str(repo),
        "sandbox_path": str(sbox),
        "commit": git.head(active_git) if active_git else "",
        "current_branch": current_branch,
        "complete_history": not git.is_shallow(repo) if has_repo else False,
        "commits": git.run(["rev-list", "--count", "HEAD"], cwd=active_git, check=False) if active_git else "0",
        "run_worktrees": len(runs),
        "python_environment": (worktrees / ".venv").exists() if worktrees.exists() else False,
        "size_mb": round(size / 1_048_576, 1),
        "sandbox_ready": has_repo,  # a sandbox is cloned from the repository, so it can exist only once one is connected
        "sandbox_initialized": has_sandbox,
    }
