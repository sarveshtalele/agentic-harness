"""Each project's sandbox: its own folder with a full clone, one worktree per run, its own Python environment.

Test code runs with clean_env(), so it cannot see platform secrets.
ponytail: this isolates by folder and environment, not by operating system. Use a container per project before running repositories you do not trust.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import asyncio
from pathlib import Path

from backend.config import project_dir, repo_dir
from backend.db import db, row
from backend.repos import git, github
from backend.core.security import safe_path


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
    """Ensure project sandbox directory and repo folder exist with valid git initialized."""
    root = project_dir(project_id)
    repo = repo_dir(project_id)
    root.mkdir(parents=True, exist_ok=True)
    repo.mkdir(parents=True, exist_ok=True)
    
    # Initialize git repo if not yet created
    if not (repo / ".git").exists():
        readme = repo / "README.md"
        if not readme.exists():
            readme.write_text(f"# Project Sandbox: {project_id}\n\nAutomated sandbox environment created by Agentic QE Platform.\n")
        git.init_snapshot(repo, f"Initial sandbox commit for {project_id}")
    return repo


def info(project_id: str) -> dict:
    root, repo = project_dir(project_id), repo_dir(project_id)
    worktrees = root / "worktrees"
    runs = [p.name for p in worktrees.iterdir() if p.is_dir() and p.name.startswith("run_") and not p.name.endswith(("-results", "-baseline"))] if worktrees.exists() else []
    size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink() and ".venv" not in p.parts) if root.exists() else 0
    has_repo = repo.exists() and (repo / ".git").exists()
    return {
        "path": str(root),
        "commit": git.head(repo) if has_repo else "",
        "complete_history": not git.is_shallow(repo) if has_repo else False,
        "commits": git.run(["rev-list", "--count", "HEAD"], cwd=repo, check=False) if has_repo else "0",
        "run_worktrees": len(runs),
        "python_environment": (worktrees / ".venv").exists() if worktrees.exists() else False,
        "size_mb": round(size / 1_048_576, 1),
        "sandbox_ready": True
    }


def clean_sandbox_env() -> dict:
    """Zero-trust allowlist of environment variables for isolated subprocess executions."""
    allowed = {"PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "SYSTEMROOT", "TEMP", "TMP"}
    env = {k: v for k, v in os.environ.items() if k in allowed}
    env["HOME"] = "/tmp"
    env["TMPDIR"] = "/tmp"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def create_file(project_id: str, rel_path: str, content: str) -> dict:
    """Create a file inside project sandbox safely."""
    repo = ensure_sandbox(project_id)
    target = safe_path(repo, rel_path, for_write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"status": "created", "path": str(target.relative_to(repo)), "size": len(content)}


def execute_code(project_id: str, code: str, runtime: str = "python", timeout: int = 60) -> dict:
    """Execute code in project sandbox with subprocess isolation."""
    repo = ensure_sandbox(project_id)
    script_file = repo / ("_sandbox_exec.py" if runtime == "python" else "_sandbox_exec.js")
    script_file.write_text(code, encoding="utf-8")
    binary = shutil.which("python3") if runtime == "python" else shutil.which("node")
    if not binary:
        return {"status": "error", "message": f"{runtime} binary not found"}
    try:
        proc = subprocess.run(
            [binary, str(script_file)],
            cwd=repo,
            env=clean_sandbox_env(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": f"Execution timed out after {timeout}s"}
    finally:
        if script_file.exists():
            script_file.unlink(missing_ok=True)


def install_dependencies(project_id: str, package: str = "", manager: str = "pip") -> dict:
    """Install dependencies in project sandbox."""
    repo = ensure_sandbox(project_id)
    cmd = []
    if manager == "npm":
        npm = shutil.which("npm")
        if not npm:
            return {"status": "error", "message": "npm not found on PATH"}
        cmd = [npm, "install"] + ([package] if package else [])
    else:
        python = shutil.which("python3")
        if not python:
            return {"status": "error", "message": "python3 not found on PATH"}
        cmd = [python, "-m", "pip", "install"] + ([package] if package else ["-r", "requirements.txt"])
    
    try:
        proc = subprocess.run(cmd, cwd=repo, env=clean_sandbox_env(), capture_output=True, text=True, timeout=300)
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

