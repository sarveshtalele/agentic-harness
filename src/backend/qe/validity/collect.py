"""V3: the test file parses, then collects or compiles with the run's own dependencies, never the platform's packages."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from backend.core.security import redact
from backend.qe import execution

NOT_INSTALLED = "not checked: dependencies were not installed. Start the run with Install dependencies on, so the file can be collected with the repository's own packages"


def run_python(worktree: Path) -> Path | None:
    """The run's own interpreter: the .venv that install_dependencies makes beside the worktree. None when the run has none."""
    python = worktree.parent / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return python if python.exists() else None


def _run(command: list[str], worktree: Path, env: dict, timeout: int) -> tuple[int, str]:
    try:
        done = subprocess.run(command, cwd=worktree, env=execution.clean_env(env), capture_output=True, text=True, errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout} seconds"
    except OSError as exc:
        return 127, str(exc)
    return done.returncode, redact((done.stdout + done.stderr).strip()[-20_000:])


def _cause(out: str) -> str:
    """The error lines of a failed run, not the warnings around them."""
    lines = out.splitlines()
    return "\n".join([line for line in lines if line.startswith("E ") or "Error" in line][-6:] or lines[-6:])[-500:]


def _python(worktree: Path, path: str, code: str) -> tuple[str, str]:
    if issue := execution.syntax_error(path, code):
        return "FAIL", f"{issue}. Fix the syntax so the file parses"
    python = run_python(worktree)
    if python is None:
        return "NOT CHECKED", NOT_INSTALLED
    env = execution.build_command("pytest", worktree, path, worktree / "unused.xml")[1]
    status, out = _run([str(python), "-m", "pytest", path, "--collect-only", "-q", "--disable-warnings", "-p", "no:cacheprovider"], worktree, env, 120)
    if status == 0:
        return "PASS", f"collected {sum('::' in line for line in out.splitlines())} test(s)"
    if status == 5:
        return "FAIL", "pytest collected no test. Name test functions test_<case id>_<what> at module level"
    return "FAIL", f"pytest could not collect it (exit {status}): {_cause(out)}. Fix the import or syntax error it names"


def _node(worktree: Path, path: str) -> tuple[str, str]:
    suffix = Path(path).suffix
    if suffix in (".js", ".mjs", ".cjs"):
        node = shutil.which("node")
        if not node:
            return "NOT CHECKED", "not checked: node is not on PATH, so the syntax of this file was not checked"
        status, out = _run([node, "--check", path], worktree, {}, 60)
        return ("PASS", "node --check passed") if status == 0 else ("FAIL", f"node --check failed: {_cause(out)}. Fix the syntax it names")
    tsc = worktree / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
    if suffix in (".ts", ".tsx") and tsc.exists():
        status, out = _run([str(tsc), "--noEmit", "--skipLibCheck", path], worktree, {}, 120)  # ponytail: one file at a time, so tsconfig.json is not applied
        return ("PASS", "tsc --noEmit passed") if status == 0 else ("FAIL", f"tsc --noEmit failed: {_cause(out)}. Fix the type or import error it names")
    return "NOT CHECKED", NOT_INSTALLED if suffix in (".ts", ".tsx") else f"not checked: no checker for {suffix} files"


def compiles(worktree: Path, path: str, code: str) -> dict:
    status, message = _python(worktree, path, code) if path.endswith(".py") else _node(worktree, path)
    return {"status": status, "message": message}
