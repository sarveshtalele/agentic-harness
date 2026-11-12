"""`aqh doctor`: what this machine gives the harness (docs/PHASE2_PLAN.md section 11.1). Names sources, never values."""
from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from aqh import server, settings

ROOT = Path(__file__).resolve().parents[2]


def report() -> str:
    sys.path[:0] = [str(ROOT / "src")]
    from backend.core import script_runtime as rt

    lines = [f"System: {platform.system()} {platform.release()}, Python {platform.python_version()}"]
    bash, ps = rt.find_bash(), rt.find_powershell()
    lines.append(f"bash: {bash or 'not found' + (' (install Git for Windows)' if platform.system() == 'Windows' else '')}")
    lines.append(f"PowerShell: {ps or 'not found (optional on macOS and Linux)'}")
    node = rt.node_version()
    lines.append(f"Node.js: {'.'.join(map(str, node)) if node else 'not found'}" + ("" if not node or node >= (22, 18) else " (TypeScript needs 22.18+, or tsx)"))
    from backend.maf.harness_kit import os_sandbox

    box = os_sandbox.kind()
    lines.append(f"OS sandbox: {box or 'none'}" + (" (auto mode runs commands inside it)" if box else
                 " (Windows has none; on Linux install bubblewrap; every command asks)"))
    for tool in ("git", "npm", "npx", "pg_ctl", "initdb"):
        lines.append(f"{tool}: {shutil.which(tool) or 'not found'}")
    model = settings.model()
    sources = model["sources"]
    lines.append("Model base URL: " + (f"set ({sources.get('base_url')})" if model.get("base_url") else "missing: `aqh config model --base-url ...`"))
    lines.append("Model name: " + (f"{model['name']} ({sources.get('name')})" if model.get("name") else "missing: `aqh config model --name ...`"))
    lines.append("Model key: " + (f"set ({sources.get('api_key')})" if model.get("api_key") else "missing: `aqh config set-key` or OPENAI_API_KEY"))
    running = server.status()
    lines.append(f"Local server: {'running at ' + running['url'] if running else 'not running (starts with the first aqh)'}")
    lines.append(f"aqh home: {settings.home()}")
    return "\n".join(lines)
