#!/usr/bin/env python3
"""One cross-platform entry point. Standard library only, so it runs before any install.

  python scripts/dev.py setup      create .venv, install Python and Node dependencies
  python scripts/dev.py db         start local PostgreSQL (data/postgres), put its URL in .env; --import-sqlite [path] copies an old store
  python scripts/dev.py backend    FastAPI on 127.0.0.1:8000
  python scripts/dev.py frontend   Next.js dev server on 127.0.0.1:3000
  python scripts/dev.py up         install if needed, build, run backend and UI, open the browser
  python scripts/dev.py start      production: build the UI, run backend and UI together
  python scripts/dev.py test       unit and integration tests (no network, no model)
  python scripts/dev.py smoke      browser smoke test on its own ports with no model (used by CI)
  python scripts/dev.py e2e        Playwright end-to-end tests against real servers and the real model
  python scripts/dev.py live [tests] live tests with the model from your local store (key never printed)
  python scripts/dev.py evidence   run tests and smoke (add --e2e for end to end) into JUnit, then write the evidence report
  python scripts/dev.py env-check --env local|azure   report missing or weak settings (no values printed)
  python scripts/dev.py azure-local  run the two Azure zips locally in the web profile (add --check to check and stop)
  python scripts/dev.py admin-password  a random first-admin password, shown once, and the hash to set as ATLAS_ADMIN_PASSWORD_HASH
"""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PYTHON = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)  # setup makes .venv; before it, this Python
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)}
BACKEND = [str(PYTHON), "-m", "uvicorn", "backend.app:app", "--host", os.environ.get("ATLAS_HOST", "127.0.0.1"), "--port", os.environ.get("ATLAS_PORT", "8000")]


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, env=ENV, check=True)


def step(number: int, total: int, text: str, started: float) -> None:
    """One live progress line, so a slow step is visible as slow, not stuck."""
    print(f"[setup {number}/{total} | {time.monotonic() - started:5.0f}s] {text}", flush=True)


def npm() -> str:
    found = shutil.which("npm")  # resolves npm.cmd on Windows, which subprocess cannot find alone
    if not found:
        sys.exit("Node.js 20+ with npm is required: https://nodejs.org")
    return found


def setup() -> None:
    if sys.version_info < (3, 12):
        sys.exit(f"Python 3.12+ is required, found {sys.version.split()[0]}")
    if not shutil.which("git"):
        sys.exit("Git is required: https://git-scm.com")
    global PYTHON
    started = time.monotonic()
    if not VENV_PYTHON.exists():  # always the project's own environment, never the global Python (found on Windows 2026-11-12)
        step(1, 4, f"Creating the Python environment in {VENV}", started)
        venv.create(VENV, with_pip=True)
    PYTHON = VENV_PYTHON
    step(2, 4, "Installing Python packages into .venv (several minutes the first time)", started)
    run([str(PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"])
    step(3, 4, "Installing Playwright's Chromium (browser tests and QE screenshots)", started)
    run([str(PYTHON), "-m", "playwright", "install", "chromium"])
    step(4, 4, "Installing UI packages with npm ci (5 to 10 minutes on Windows the first time)", started)
    run([npm(), "ci", "--no-audit", "--no-fund"], FRONTEND)
    step(4, 4, "Done. Next: python scripts/dev.py db", started)
    if not (ROOT / ".env").exists():
        import secrets  # a fresh .env gets a working admin sign-in: 24 random characters, shown once here and kept only in .env
        password = secrets.token_urlsafe(18)
        text = (ROOT / ".env.example").read_text(encoding="utf-8").replace("ATLAS_ADMIN_USERNAME=\n", "ATLAS_ADMIN_USERNAME=admin\n")
        (ROOT / ".env").write_text(text.replace("ATLAS_ADMIN_PASSWORD=\n", f"ATLAS_ADMIN_PASSWORD={password}\n"), encoding="utf-8")
        print(f"Created .env. Sign in as admin with the password {password} (also in .env). Add model settings there or in Settings.")


def _port_free(port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


def _spawn(command: list[str], cwd: Path, env: dict) -> subprocess.Popen:
    # each server gets its own process group, because npm starts child processes that must stop with it
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    return subprocess.Popen(command, cwd=cwd, env=env, **options)


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=30)
    else:
        os.killpg(process.pid, signal.SIGTERM)


def _needs_build(dist: Path) -> bool:
    built = dist / "BUILD_ID"
    if not built.exists():
        return True
    stamp = built.stat().st_mtime
    watched = [FRONTEND / name for name in ("app", "components", "features", "lib", "next.config.ts", "package-lock.json")]
    return any(f.stat().st_mtime > stamp for item in watched for f in ([item] if item.is_file() else item.rglob("*")) if f.is_file())


def _database(env: dict) -> None:
    """Start the local PostgreSQL (data/postgres) when the app uses one, every time: after a reboot, or when `dev.py db`
    ran in a window that is gone, nothing else starts it. A remote database (Azure) is left alone."""
    lines = (ROOT / ".env").read_text(encoding="utf-8").splitlines() if (ROOT / ".env").is_file() else []
    url = os.environ.get("ATLAS_DATABASE_URL") or next((l.split("=", 1)[1].strip().strip('"\'') for l in lines if l.strip().startswith("ATLAS_DATABASE_URL=")), "")
    if url and urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        return
    run([str(PYTHON), str(ROOT / "scripts" / "pg_local.py")])  # starts it if stopped and writes its URL to .env
    env.pop("ATLAS_DATABASE_URL", None)  # a stale local URL in the system environment would win over the fresh one in .env


def _wait(url: str, processes: list, what: str, seconds: int = 180) -> None:
    for _ in range(seconds):
        if any(p.poll() is not None for p in processes):
            sys.exit(f"The {what} stopped during startup. See the messages above.")
        try:
            urllib.request.urlopen(url, timeout=2).close()
            return
        except OSError:
            time.sleep(1)
    sys.exit(f"The {what} did not answer at {url} within {seconds // 60} minutes. See the messages above.")


def up() -> None:
    """The launchers call this: one command from a fresh checkout to the app in a browser.
    Order: dependencies, the UI build, the database, the backend (waited for), then the UI, so nothing waits on a server
    that is not there yet."""
    api_port, ui_port = int(os.environ.get("ATLAS_PORT", "8000")), int(os.environ.get("ATLAS_UI_PORT", "3000"))
    for port in (api_port, ui_port):
        if not _port_free(port):
            sys.exit(f"Port {port} is in use. Stop what is using it, or set ATLAS_PORT and ATLAS_UI_PORT to free ports.")
    if not PYTHON.exists() or not (FRONTEND / "node_modules").exists():
        print("First run: installing dependencies. This takes a few minutes.")
        setup()
    env = {**ENV, "ATLAS_BACKEND_URL": os.environ.get("ATLAS_BACKEND_URL", f"http://127.0.0.1:{api_port}"), "NEXT_TELEMETRY_DISABLED": "1"}
    env.setdefault("ATLAS_ALLOWED_ORIGINS", f"http://127.0.0.1:{ui_port},http://localhost:{ui_port}")
    if _needs_build(FRONTEND / os.environ.get("ATLAS_DIST_DIR", ".next")):
        print("Building the UI.")
        subprocess.run([npm(), "run", "build"], cwd=FRONTEND, env=env, check=True)
    _database(env)
    backend = _spawn([str(PYTHON), "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", str(api_port)], ROOT, env)
    frontend, url = None, f"http://127.0.0.1:{ui_port}"
    try:
        print("Starting the backend.")
        _wait(f"http://127.0.0.1:{api_port}/api/health", [backend], "backend")
        frontend = _spawn([npm(), "run", "start", "--", "--hostname", "127.0.0.1", "--port", str(ui_port)], FRONTEND, env)
        _wait(f"{url}/login", [backend, frontend], "UI")
        print(f"\nAgentic QE Platform is running at {url}. Press Ctrl+C to stop.\n", flush=True)
        if not os.environ.get("ATLAS_NO_BROWSER"):
            webbrowser.open(url)
        while not os.environ.get("ATLAS_UP_CHECK") and backend.poll() is None and frontend.poll() is None:  # CI: started, so stop
            time.sleep(1)
    finally:
        if frontend:
            _stop(frontend)
        _stop(backend)


COMMANDS = {
    "db": lambda: run([str(PYTHON), str(ROOT / "scripts" / "pg_local.py"), *sys.argv[2:]]),
    "evidence": lambda: run([str(PYTHON), str(ROOT / "scripts" / "evidence_run.py"), *sys.argv[2:]]),
    "env-check": lambda: run([sys.executable, str(ROOT / "scripts" / "env_check.py"), *sys.argv[2:]]),
    "azure-local": lambda: run([str(PYTHON), str(ROOT / "scripts" / "azure_local.py"), *sys.argv[2:]]),  # needs psycopg for its local PostgreSQL
    "up": up,
    "setup": setup,
    "backend": lambda: run(BACKEND),
    "frontend": lambda: run([npm(), "run", "dev", "--", "--hostname", "127.0.0.1"], FRONTEND),
    "start": lambda: (os.environ.setdefault("ATLAS_NO_BROWSER", "1"), up()),  # production: the same order as up, no browser
    "test": lambda: run([str(PYTHON), "-m", "pytest", "tests", "-q", "-m", "not e2e and not live and not smoke"]),
    "smoke": lambda: run([str(PYTHON), "-m", "pytest", "tests/e2e/test_smoke.py", "-v", "-m", "smoke"]),
    "e2e": lambda: run([str(PYTHON), "-m", "pytest", "tests/e2e", "-v", "-m", "e2e", "-s"]),
    "admin-password": lambda: run([str(PYTHON), str(ROOT / "scripts" / "admin_password.py")]),
    "live": lambda: run([str(PYTHON), str(ROOT / "scripts" / "run_live.py"), *sys.argv[2:]]),  # real model from your local store
}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in COMMANDS:
        sys.exit(__doc__)
    try:
        COMMANDS[action]()
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
