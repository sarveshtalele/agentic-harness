"""File, branch and commit operations inside the project sandbox."""
from __future__ import annotations

from backend.config import sandbox_dir
from backend.repos import git
from backend.core.security import safe_path
from backend.repos.sandbox.setup import ensure_sandbox


def create_file(project_id: str, rel_path: str, content: str, target: str = "auto") -> dict:
    """Create a file inside project sandbox safely."""
    repo = ensure_sandbox(project_id)
    sbox = sandbox_dir(project_id)
    
    # Primary target
    if target == "sandbox" and sbox.exists():
        primary = safe_path(sbox, rel_path, for_write=True)
    else:
        primary = safe_path(repo, rel_path, for_write=True)

    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(content, encoding="utf-8")

    # Keep both repo and sandbox synced when auto
    if target == "auto" and sbox.exists() and sbox != repo:
        try:
            sec = safe_path(sbox, rel_path, for_write=True)
            sec.parent.mkdir(parents=True, exist_ok=True)
            sec.write_text(content, encoding="utf-8")
        except Exception:
            pass
    elif target == "sandbox" and repo.exists() and repo != sbox:
        try:
            sec = safe_path(repo, rel_path, for_write=True)
            sec.parent.mkdir(parents=True, exist_ok=True)
            sec.write_text(content, encoding="utf-8")
        except Exception:
            pass

    return {"status": "created", "path": rel_path, "size": len(content)}


def create_branch(project_id: str, branch_name: str, in_sandbox: bool = True) -> dict:
    """Create and checkout a new git branch in sandbox or repo."""
    sbox = sandbox_dir(project_id)
    repo = ensure_sandbox(project_id)
    work_dir = sbox if in_sandbox and sbox.exists() else repo

    try:
        git.run(["checkout", "-B", branch_name], cwd=work_dir)
        return {"status": "success", "branch": branch_name, "cwd": str(work_dir)}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "branch": branch_name}


def commit_changes(project_id: str, message: str, in_sandbox: bool = True) -> dict:
    """Stage all changes and commit in sandbox or repo."""
    sbox = sandbox_dir(project_id)
    repo = ensure_sandbox(project_id)
    work_dir = sbox if in_sandbox and sbox.exists() else repo

    try:
        sha = git.commit_all(work_dir, message)
        return {"status": "success", "commit": sha, "message": message, "cwd": str(work_dir)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
