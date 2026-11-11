"""Run code and install dependencies in the project sandbox."""
from __future__ import annotations

import shutil
import subprocess

from backend.repos.sandbox.env import clean_sandbox_env
from backend.repos.sandbox.setup import ensure_sandbox


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
            timeout=timeout,
            shell=False,
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
        proc = subprocess.run(cmd, cwd=repo, env=clean_sandbox_env(), capture_output=True, text=True, timeout=300, shell=False)
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
