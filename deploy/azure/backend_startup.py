"""App Service startup for the backend. Builds the Python environment once per requirements change, then serves.

Portal startup command: python /home/site/wwwroot/startup.py
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import toolchains  # deploy/azure/toolchains.py, shipped next to this file as toolchains.py

APP = Path(__file__).resolve().parent
HOME = Path(os.environ.get("ATLAS_HOME", "/home/atlas"))
VENV = HOME / "venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
STAMP = VENV / ".atlas-stamp"


def log(message: str) -> None:
    print(f"[agentic-qe] {message}", flush=True)


EVALS = os.environ.get("ATLAS_INSTALL_EVALS") == "1" and (APP / "requirements-evals.txt").is_file()  # RAGAS for faithfulness scores


def wanted_stamp() -> str:
    evals = (APP / "requirements-evals.txt").read_bytes() if EVALS else b""
    return hashlib.sha256((APP / "requirements.txt").read_bytes() + evals + sys.version.encode()).hexdigest()


def build() -> None:
    wanted = wanted_stamp()
    if PYTHON.exists() and STAMP.exists() and STAMP.read_text() == wanted:
        log("Environment is current; skipping install")
        return
    log(f"Building environment in {VENV}. The first run takes several minutes")
    HOME.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True, timeout=300)
    subprocess.run([str(PYTHON), "-m", "pip", "install", "--no-input", "--disable-pip-version-check", "-r", str(APP / "requirements.txt")], check=True, timeout=1500)
    if EVALS:
        log("Installing evaluation packages (RAGAS)")
        subprocess.run([str(PYTHON), "-m", "pip", "install", "--no-input", "--disable-pip-version-check", "-r", str(APP / "requirements-evals.txt")], check=True, timeout=1500)
    STAMP.write_text(wanted)
    log("Environment built")


def start_toolchains(env: dict) -> None:
    """Install Node, JDK, Maven, .NET, Go and Chromium into /home/tools in the background, so the API is up at once.
    Greenfield runs need them; the log and /home/tools/status.json say which are ready. ATLAS_INSTALL_TOOLCHAINS=none skips."""
    if not toolchains.supported():
        log("Toolchains: not Linux x64, none installed here (see toolchains.py)")
        return
    if not toolchains.wanted(env.get("ATLAS_INSTALL_TOOLCHAINS")):
        log("Toolchains: skipped, ATLAS_INSTALL_TOOLCHAINS=none. Greenfield runs will report the missing tools")
        return
    log(f"Toolchains: installing in the background into {toolchains.ROOT}; progress in this log and {toolchains.ROOT / 'status.json'}")
    subprocess.Popen([str(PYTHON), str(APP / "toolchains.py"), "--python", str(PYTHON)], env=env, start_new_session=True, stdin=subprocess.DEVNULL)


def main() -> None:
    build()
    # the venv goes first on PATH so the app finds ruff and other tools installed there; the toolchains in /home/tools follow it.
    # The API process owns this environment, and clean_sandbox_env (repos/sandbox/env.py) hands PATH, JAVA_HOME, GOROOT,
    # DOTNET_ROOT and PLAYWRIGHT_BROWSERS_PATH on to every sandbox command, so a project's sandbox sees the same tools.
    env = {**os.environ, "PYTHONPATH": f"{APP / 'src'}{os.pathsep}{APP}"}
    env.update(toolchains.tool_env(base_path=f"{PYTHON.parent}{os.pathsep}{os.environ.get('PATH', '')}"))
    start_toolchains(env)
    # files on the persistent /home share; the database is PostgreSQL, its URL read from Key Vault at startup (backend/keyvault.py)
    env.setdefault("ATLAS_DATA_DIR", str(HOME / "data"))
    port = os.environ.get("PORT", "8000")
    log(f"Starting API on port {port}")
    os.chdir(APP)
    # one worker on purpose: running workflows live in this process. ponytail: scale up, not out, until runs move to a queue
    os.execve(str(PYTHON), [str(PYTHON), "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", port, "--workers", "1", "--proxy-headers"], env)


if __name__ == "__main__":
    main()
