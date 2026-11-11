"""Dependency installation in a run worktree."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from backend.qe.execution.runners import GIT_AUTHOR, clean_env, detect_python


def _commit_date(worktree: Path) -> str:
    """Date of the newest commit this app did not make. Its own commit moments ago would remove the date limit."""
    done = subprocess.run([shutil.which("git") or "git", "log", "-50", "--format=%an|%cI"], cwd=worktree, capture_output=True, text=True, timeout=30)
    dates = [line.rsplit("|", 1) for line in done.stdout.splitlines() if "|" in line]
    return next((date for author, date in dates if author != GIT_AUTHOR), "")


def _test_extras(worktree: Path) -> str:
    """The repository's own test plugins usually live in dev or test extras, and tests cannot run without them."""
    try:
        extras = tomllib.loads((worktree / "pyproject.toml").read_text(encoding="utf-8")).get("project", {}).get("optional-dependencies", {})
    except (tomllib.TOMLDecodeError, OSError):
        return ""
    wanted = [name for name in extras if name.lower() in {"dev", "test", "tests", "testing"}]
    return f"[{','.join(wanted)}]" if wanted else ""


def install_dependencies(worktree: Path, analysis: dict, log) -> None:
    """Runs repo-defined install scripts, so callers only reach this after explicit human opt-in.

    Unpinned dependencies install as they were at the repository's last commit, because a later major
    release can break code that was fine when written.
    """
    if (worktree / "requirements.txt").exists() or (worktree / "pyproject.toml").exists():
        venv = worktree.parent / ".venv"
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=False, timeout=120)
        subprocess.run([str(python), "-m", "pip", "install", "-q", "-U", "pip"], env=clean_env(), capture_output=True, timeout=180)
        supported = "--uploaded-prior-to" in subprocess.run([str(python), "-m", "pip", "install", "--help"], capture_output=True, text=True, errors="replace", timeout=60).stdout
        date = _commit_date(worktree)
        dated = ["--uploaded-prior-to", date] if supported and date else []
        log(f"Installing dependencies as of {date}" if dated else "Installing latest dependencies; this pip cannot limit by date")
        steps = []
        if (worktree / "requirements.txt").exists():
            steps.append([str(python), "-m", "pip", "install", "-q", *dated, "-r", "requirements.txt"])
        if (worktree / "pyproject.toml").exists():
            steps.append([str(python), "-m", "pip", "install", "-q", *dated, "-e", f".{_test_extras(worktree)}"])
        steps += [[str(python), "-m", "pip", "install", "-q", *dated, "-r", path.name] for path in sorted(worktree.glob("requirements*dev*.txt")) + sorted(worktree.glob("requirements*test*.txt"))]
        steps.append([str(python), "-m", "pip", "install", "-q", *dated, "pytest"])
        for step in steps:
            done = subprocess.run(step, cwd=worktree, env=clean_env(), capture_output=True, text=True, errors="replace", timeout=600)
            log(f"pip exit {done.returncode}: {' '.join(step[4:])[:120]}" + (f" {done.stderr.strip()[-200:]}" if done.returncode else ""))
    npm = shutil.which("npm")
    if (worktree / "package.json").exists() and npm:
        command = [npm, "ci"] if (worktree / "package-lock.json").exists() else [npm, "install"]
        done = subprocess.run(command, cwd=worktree, env=clean_env(), capture_output=True, text=True, errors="replace", timeout=900)
        log(f"{' '.join(command[1:])} exit {done.returncode}")


def async_test_files(worktree: Path, target: str = "tests/agentic_qe") -> list[str]:
    folder = worktree / target
    if not folder.is_dir():
        return []
    return sorted(p.relative_to(worktree).as_posix() for p in folder.rglob("*.py") if re.search(r"^\s*async def test_|pytest\.mark\.asyncio", p.read_text(encoding="utf-8", errors="replace"), re.M))


def install_pytest_asyncio(worktree: Path, log) -> bool:
    """Argument list, no shell, a timeout, and the scrubbed environment. Only reached after the run's install opt-in."""
    python = detect_python(worktree)
    done = subprocess.run([python, "-m", "pip", "install", "-q", "pytest-asyncio"], cwd=worktree, env=clean_env(), capture_output=True, text=True, errors="replace", timeout=300)
    log(f"pip exit {done.returncode}: pytest-asyncio" + (f" {done.stderr.strip()[-200:]}" if done.returncode else ""))
    return done.returncode == 0
