"""The local backend `aqh` talks to (docs/PHASE2_PLAN.md section 11.1, local mode).

Started once per machine user and reused by every `aqh` until `aqh server stop`: a PostgreSQL cluster in `~/.aqh/postgres`
(`backend/local_postgres.py`, the same one the desktop app and tests use) and the platform's API on 127.0.0.1 with the
`cli` profile, its data in `~/.aqh/data`. The local admin account and the secret key are random, made once, kept in the
OS keychain (or an owner-only file where no keychain exists) and handed to the server through its environment only.
The model's base URL, name and key come from `aqh.settings` the same way.
"""
from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from aqh import settings

ROOT = Path(__file__).resolve().parents[2]
WAIT_S = 120


def _state_file() -> Path:
    return settings.home() / "server.json"


def credentials() -> dict:
    """The local admin and the server's secret key, created on first use."""
    try:
        import keyring

        stored = keyring.get_password(settings.SERVICE, "local-server")
        if stored:
            return json.loads(stored)
        made = {"username": "aqh", "password": secrets.token_urlsafe(24), "secret_key": secrets.token_urlsafe(48)}
        keyring.set_password(settings.SERVICE, "local-server", json.dumps(made))
        return made
    except Exception:  # noqa: BLE001 - no keychain: an owner-only file in ~/.aqh instead
        path = settings.home() / "local-server.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        made = {"username": "aqh", "password": secrets.token_urlsafe(24), "secret_key": secrets.token_urlsafe(48)}
        path.write_text(json.dumps(made), encoding="utf-8")
        if os.name != "nt":
            path.chmod(0o600)
        return made


def status() -> dict | None:
    """The running server's {"url", "pid", "port"}, or None when none answers."""
    path = _state_file()
    if not path.is_file():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    try:
        if httpx.get(f"{state['url']}/api/health", timeout=3).status_code == 200:
            return state
    except httpx.HTTPError:
        pass
    return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(model: dict, say=print) -> dict:
    if found := status():
        return found
    sys.path[:0] = [str(ROOT / "src")]
    from backend.local_postgres import start as start_postgres

    database = start_postgres(settings.home() / "postgres", say=lambda text: say(f"[aqh] {text}"))
    creds, port = credentials(), _free_port()
    env = {**os.environ, "ATLAS_PROFILE": "cli", "ATLAS_DATA_DIR": str(settings.home() / "data"), "ATLAS_DATABASE_URL": database,
           "ATLAS_ADMIN_USERNAME": creds["username"], "ATLAS_ADMIN_PASSWORD": creds["password"], "ATLAS_SECRET_KEY": creds["secret_key"],
           "ATLAS_ALLOWED_ORIGINS": f"http://127.0.0.1:{port}", "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)])}
    for field, key in (("base_url", "OPENAI_BASE_URL"), ("name", "DEFAULT_MODEL"), ("api_key", "OPENAI_API_KEY")):
        if model.get(field):
            env[key] = model[field]
    logs = settings.home() / "logs"
    logs.mkdir(exist_ok=True)
    detach = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)} if os.name == "nt" else {"start_new_session": True}
    with (logs / "server.log").open("ab") as log:
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", str(port)],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **detach)
    state = {"url": f"http://127.0.0.1:{port}", "pid": proc.pid, "port": port}
    _state_file().write_text(json.dumps(state), encoding="utf-8")
    say(f"[aqh] starting the local server on {state['url']} (log: {logs / 'server.log'})")
    deadline = time.monotonic() + WAIT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"The local server stopped while starting; see {logs / 'server.log'}")
        if status():
            return state
        time.sleep(0.5)
    raise RuntimeError(f"The local server did not answer within {WAIT_S} s; see {logs / 'server.log'}")


def stop() -> str:
    path = _state_file()
    if not path.is_file():
        return "No local server is recorded."
    state = json.loads(path.read_text(encoding="utf-8"))
    try:
        import psutil

        proc = psutil.Process(state["pid"])
        for p in [proc, *proc.children(recursive=True)]:
            p.terminate()
        psutil.wait_procs([proc], timeout=10)
    except Exception:  # noqa: BLE001 - already gone
        pass
    path.unlink()
    sys.path[:0] = [str(ROOT / "src")]
    from backend.local_postgres import stop as stop_postgres

    stop_postgres(settings.home() / "postgres")
    return f"Stopped the local server on {state['url']} and its PostgreSQL."
