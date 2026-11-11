#!/usr/bin/env python3
"""Run the two Azure zips locally, through their own startup scripts, in the web profile (docs/AZURE_POC_PORTAL_GUIDE.md section 10).

  python scripts/dev.py azure-local            build the zips, start both apps, keep running until Ctrl+C
  python scripts/dev.py azure-local --check    same, then check the pages answer and stop

The admin comes from ATLAS_ADMIN_USERNAME and ATLAS_ADMIN_PASSWORD in the environment (never from argv).
Ports: ATLAS_AZURE_API_PORT (default 8030) and ATLAS_AZURE_UI_PORT (default 3030). State goes to data/azure-local/.
Standard library only.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "azure-local"


def _wait(url: str, seconds: int) -> int:
    """HTTP status of url once it answers, or 0 if it never did."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except OSError:
            time.sleep(3)
    return 0


def _unpack(name: str) -> Path:
    target = WORK / name / "wwwroot"
    if target.exists():
        shutil.rmtree(target)  # ponytail: only our own unpack folder under data/azure-local is replaced
    target.mkdir(parents=True)
    with zipfile.ZipFile(ROOT / "dist" / f"azure_{name}.zip") as bundle:
        for member in bundle.namelist():  # zip-slip guard, although we built this zip ourselves
            if not (target / member).resolve().is_relative_to(target.resolve()):
                raise SystemExit(f"Refusing zip member outside the folder: {member}")
        bundle.extractall(target)
    return target


def main() -> int:
    user, password = os.environ.get("ATLAS_ADMIN_USERNAME"), os.environ.get("ATLAS_ADMIN_PASSWORD")
    if not (user and password):
        raise SystemExit("Set ATLAS_ADMIN_USERNAME and ATLAS_ADMIN_PASSWORD in the environment first, as the App Service settings do.")
    api_port, ui_port = os.environ.get("ATLAS_AZURE_API_PORT", "8030"), os.environ.get("ATLAS_AZURE_UI_PORT", "3030")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "package_azure_kudu.py")], cwd=ROOT, check=True, timeout=900)
    api_dir, ui_dir = _unpack("backend"), _unpack("frontend")
    base = {k: v for k, v in os.environ.items() if not k.startswith("ATLAS_")}  # only what App Service would set
    sys.path.insert(0, str(ROOT))
    from scripts import pg_local  # stands in for Azure Database for PostgreSQL (atlas-database-url in Key Vault)

    database = pg_local.start(WORK / "postgres")
    api_env = {**base, "ATLAS_PROFILE": "web", "ATLAS_HOME": str(WORK / "backend" / "home"), "PORT": api_port, "ATLAS_DATABASE_URL": database,
               "ATLAS_ADMIN_USERNAME": user, "ATLAS_ADMIN_PASSWORD": password, "ATLAS_ALLOWED_ORIGINS": f"http://127.0.0.1:{ui_port},http://localhost:{ui_port}"}
    ui_env = {**base, "ATLAS_HOME": str(WORK / "frontend" / "home"), "PORT": ui_port, "ATLAS_BACKEND_URL": f"http://127.0.0.1:{api_port}"}
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is not on PATH")
    api = subprocess.Popen([sys.executable, str(api_dir / "startup.py")], cwd=api_dir, env=api_env)
    ui = subprocess.Popen([node, str(ui_dir / "startup.js")], cwd=ui_dir, env=ui_env)
    try:
        health = _wait(f"http://127.0.0.1:{api_port}/api/health", 1500)
        login = _wait(f"http://127.0.0.1:{ui_port}/login", 1500)
        print(f"API health: {health or 'no answer'}; UI /login: {login or 'no answer'}; UI at http://127.0.0.1:{ui_port}", flush=True)
        if "--check" in sys.argv:
            return 0 if health == 200 and login == 200 else 1
        while api.poll() is None and ui.poll() is None:
            time.sleep(1)
        return 1
    finally:
        for process in (ui, api):
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
