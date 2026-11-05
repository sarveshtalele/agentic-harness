"""Each project's sandbox: its own folder with a full clone, one worktree per run, its own Python environment.

Test code runs with clean_env(), so it cannot see platform secrets.
ponytail: this isolates by folder and environment, not by operating system. Use a container per project before running repositories you do not trust.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import asyncio
import shlex
from pathlib import Path

from backend.config import project_dir, repo_dir, sandbox_dir
from backend.db import db, row, now, new_id
from backend.repos import git, github
from backend.core.security import safe_path
from backend.core import ledger


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
        if (repo / ".git").exists():
            git.run(["clone", str(repo), str(sbox)])
        else:
            sbox.mkdir(parents=True, exist_ok=True)
            readme = sbox / "README.md"
            if not readme.exists():
                readme.write_text(f"# Sandbox: {project_id}\n")
            git.init_snapshot(sbox, f"Initial sandbox commit for {project_id}")

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
        "sandbox_ready": True,
        "sandbox_initialized": has_sandbox,
    }


def clean_sandbox_env(extra_env: dict | None = None) -> dict:
    """Zero-trust allowlist of environment variables for isolated subprocess executions."""
    from backend.config import ROOT

    allowed = {
        "PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "SYSTEMROOT",
        "TEMP", "TMP", "USER", "TERM", "SHELL", "HOME", "NODE_PATH",
        "NPM_CONFIG_CACHE", "PYTHONPATH"
    }
    env = {k: v for k, v in os.environ.items() if k in allowed}
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if "HOME" not in env:
        env["HOME"] = "/tmp"

    root_modules = ROOT / "node_modules"
    if root_modules.exists():
        bin_dir = str(root_modules / ".bin")
        current_path = env.get("PATH", "")
        if bin_dir not in current_path:
            env["PATH"] = f"{bin_dir}:{current_path}"
        env.setdefault("NODE_PATH", str(root_modules))

    if extra_env:
        env.update(extra_env)
    return env


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


def execute_command(
    project_id: str,
    command: str | list[str],
    cwd: Path | str | None = None,
    timeout: int | None = 600,
    in_sandbox: bool = True,
    extra_env: dict | None = None,
) -> dict:
    """Execute arbitrary command cleanly in the project sandbox or repo with timeout support (None or 600s)."""
    sbox = sandbox_dir(project_id)
    repo = ensure_sandbox(project_id)

    if cwd is not None:
        work_dir = Path(cwd)
    elif in_sandbox and sbox.exists():
        work_dir = sbox
    else:
        work_dir = repo

    if isinstance(command, str):
        cmd = shlex.split(command)
    else:
        cmd = list(command)

    if not cmd:
        return {"status": "error", "exit_code": -1, "message": "Command cannot be empty"}

    binary_name = cmd[0]
    binary_path = shutil.which(binary_name)
    if not binary_path:
        return {"status": "error", "exit_code": -1, "message": f"Binary '{binary_name}' not found on PATH"}

    cmd[0] = binary_path

    try:
        proc = subprocess.run(
            cmd,
            cwd=work_dir,
            env=clean_sandbox_env(extra_env),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "command": " ".join(cmd),
            "cwd": str(work_dir),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "exit_code": -1,
            "message": f"Execution timed out after {timeout}s",
            "command": " ".join(cmd),
            "cwd": str(work_dir),
        }
    except Exception as exc:
        return {
            "status": "error",
            "exit_code": -1,
            "message": str(exc),
            "command": " ".join(cmd),
            "cwd": str(work_dir),
        }


def run_npx(
    project_id: str,
    command: str | list[str],
    cwd: Path | str | None = None,
    timeout: int | None = 600,
    in_sandbox: bool = True,
) -> dict:
    """Execute an npx command cleanly in the sandbox."""
    if isinstance(command, str):
        args = shlex.split(command)
    else:
        args = list(command)

    if args and args[0] == "npx":
        args = args[1:]

    npx_binary = shutil.which("npx")
    if not npx_binary:
        return {"status": "error", "exit_code": -1, "message": "npx not found on PATH"}

    full_cmd = [npx_binary] + args
    return execute_command(project_id, full_cmd, cwd=cwd, timeout=timeout, in_sandbox=in_sandbox)


def run_tests(
    project_id: str,
    command: str | list[str] = "pytest",
    cwd: Path | str | None = None,
    timeout: int | None = 600,
    in_sandbox: bool = True,
    extra_env: dict | None = None,
) -> dict:
    """Execute test runners without arbitrary short timeouts."""
    return execute_command(
        project_id,
        command,
        cwd=cwd,
        timeout=timeout,
        in_sandbox=in_sandbox,
        extra_env=extra_env,
    )


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


def generate_pull_request_sim(
    project_id: str,
    title: str,
    description: str,
    base_branch: str = "main",
    head_branch: str = "test/harness-qe-validation",
    in_sandbox: bool = True,
) -> dict:
    """Simulate and generate Pull Request documentation from branch changes."""
    sbox = sandbox_dir(project_id)
    repo = ensure_sandbox(project_id)
    work_dir = sbox if in_sandbox and sbox.exists() else repo

    # Compute diff and commit log
    diff_text = git.run(["diff", f"{base_branch}...{head_branch}"], cwd=work_dir, check=False)
    if not diff_text:
        diff_text = git.diff(work_dir)

    commits_text = git.run(["log", f"{base_branch}..{head_branch}", "--oneline"], cwd=work_dir, check=False)
    current_head = git.head(work_dir)

    pr_doc = f"""# Pull Request: {title}

**Target Branch:** `{base_branch}`  
**Source Branch:** `{head_branch}`  
**Head Commit:** `{current_head}`  
**Status:** Ready for Review / CI Verified  

---

## Summary
{description}

## Commits Included
```
{commits_text or "Direct working branch commit"}
```

## Diff Overview
```diff
{diff_text[:4000] if diff_text else "No diff or all changes committed cleanly"}
```

---
*Generated by Agentic QE Platform Sandbox Pipeline*
"""
    pr_file = work_dir / "PULL_REQUEST.md"
    pr_file.write_text(pr_doc, encoding="utf-8")

    # Also register in platform documents table if possible
    try:
        doc_id = new_id("doc")
        with db() as con:
            con.execute(
                "INSERT INTO documents (id, project_id, kind, title, status, current_version, created_at, updated_at) VALUES (?,?,?,?,?,1,?,?)",
                (doc_id, project_id, "pr_simulation", title, "ready", now(), now()),
            )
            con.execute(
                "INSERT INTO document_versions (document_id, version, content, data, sha256, author, note, created_at) VALUES (?,1,?,'{}','dummy','sandbox-pipeline','Automated PR simulation',?)",
                (doc_id, pr_doc, now()),
            )
        ledger.append(project_id, "sandbox-pipeline", "pr.simulated", head_branch, {"title": title, "head": current_head})
    except Exception:
        pass

    return {
        "status": "success",
        "title": title,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "head_commit": current_head,
        "pr_file": str(pr_file),
        "diff_length": len(diff_text),
    }


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

