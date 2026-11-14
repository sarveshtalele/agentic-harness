"""Container entrypoint: the API on loopback, the UI on the public port. Exits when either process exits.

Same processes and environment names as the zip deployment (startup.py, startup.js). The secrets are read from Key Vault
by the API at startup (ATLAS_KEY_VAULT_URL); nothing secret is in the image or in argv.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

UI = Path("/opt/ui")
API_PORT = os.environ.get("ATLAS_API_PORT", "8000")
UI_PORT = os.environ.get("PORT", "3000")


def log(message: str) -> None:
    print(f"[agentic-qe] {message}", flush=True)


def main() -> int:
    api_env = {**os.environ, "PYTHONPATH": f"/app/src{os.pathsep}/app"}
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", API_PORT, "--workers", "1", "--proxy-headers"],
        cwd="/app", env=api_env,
    )  # one worker on purpose: running workflows live in this process. ponytail: scale up, not out, until runs move to a queue
    server = UI / "server.js"
    if not server.exists():
        server = UI / "src" / "frontend" / "server.js"
    ui = subprocess.Popen(["node", str(server)], cwd=str(server.parent), env={**os.environ, "HOSTNAME": "0.0.0.0", "PORT": UI_PORT, "NODE_ENV": "production"})
    log(f"API on 127.0.0.1:{API_PORT}, UI on 0.0.0.0:{UI_PORT}")
    procs = [api, ui]
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: [p.terminate() for p in procs])
    while all(p.poll() is None for p in procs):
        time.sleep(1)
    for p in procs:
        if p.poll() is None:
            p.terminate()
    code = next((p.returncode for p in procs if p.returncode), 0)
    log(f"A process exited (code {code}); stopping")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
