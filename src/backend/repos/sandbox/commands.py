"""Run commands and code in the project sandbox with no shell and a timeout."""
from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from backend.config import project_dir, sandbox_dir
from backend.repos.sandbox.env import clean_sandbox_env
from backend.repos.sandbox.setup import ensure_sandbox


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
    boundary = project_dir(project_id).resolve()

    if cwd is not None:
        work_dir = Path(cwd).resolve()
        if not work_dir.is_relative_to(boundary):
            return {
                "status": "error",
                "exit_code": -1,
                "message": f"Working directory escapes project sandbox boundary: {cwd}",
                "cwd": str(work_dir),
            }
    elif in_sandbox and sbox.exists():
        work_dir = sbox.resolve()
    else:
        work_dir = repo.resolve()

    if isinstance(command, str):
        cmd = shlex.split(command)
    elif isinstance(command, (list, tuple)):
        cmd = [str(a) for a in command]
    else:
        return {"status": "error", "exit_code": -1, "message": "Command must be string or list"}

    if not cmd:
        return {"status": "error", "exit_code": -1, "message": "Command cannot be empty"}

    # Strictly disallow NUL bytes in arguments
    if any("\x00" in str(arg) for arg in cmd):
        return {"status": "error", "exit_code": -1, "message": "Command contains NUL byte"}

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
            shell=False,
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
    """Execute an npx command cleanly in the sandbox, checking for argument injection."""
    if isinstance(command, str):
        args = shlex.split(command)
    elif isinstance(command, (list, tuple)):
        args = [str(a) for a in command]
    else:
        return {"status": "error", "exit_code": -1, "message": "Command must be string or list"}

    if args and args[0] == "npx":
        args = args[1:]

    # Defend against argument injection and shell escapes in npx
    dangerous_flags = {"--shell", "--call", "-c", "/bin/sh", "/bin/bash", "sh", "bash"}
    if any(arg.strip() in dangerous_flags for arg in args):
        return {"status": "error", "exit_code": -1, "message": "Disallowed argument or shell escape in npx command"}

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
