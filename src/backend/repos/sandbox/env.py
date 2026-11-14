"""Zero-trust environment allowlist for sandbox subprocesses."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
import re


SENSITIVE_ENV_PATTERN = re.compile(
    r"(?i)(key|secret|token|password|passwd|auth|cred|atlas|openai|anthropic|aws|github|bearer|private)"
)


def _without_platform(env: dict, root: Path) -> None:
    """Repository code must not run in the platform's own Python (live run 2026-11-13: `python3` in the workspace was the
    platform's .venv with mcp 2.3 while the repository needs mcp 1.x, and its tests failed for that reason). Drop the
    platform's virtual environment from PATH and the platform's folders from PYTHONPATH."""
    venv_bin = Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin") if sys.prefix != sys.base_prefix else None
    keep = lambda p, inside: p and not (inside and Path(p).resolve().is_relative_to(inside))  # noqa: E731
    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if keep(p, venv_bin.resolve() if venv_bin else None))
    python_path = os.pathsep.join(p for p in env.get("PYTHONPATH", "").split(os.pathsep) if keep(p, root.resolve()))
    if python_path:
        env["PYTHONPATH"] = python_path
    else:
        env.pop("PYTHONPATH", None)


def playwright_browsers() -> str:
    """The folder `playwright install` filled for this account (Playwright's own default per OS), when it exists."""
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return os.environ["PLAYWRIGHT_BROWSERS_PATH"]
    home = Path.home()
    folder = (Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / "ms-playwright" if os.name == "nt"
              else home / "Library" / "Caches" / "ms-playwright" if sys.platform == "darwin" else home / ".cache" / "ms-playwright")
    return str(folder) if folder.is_dir() else ""


def clean_sandbox_env(extra_env: dict | None = None) -> dict:
    """Zero-trust allowlist of environment variables for isolated subprocess executions.
    Ambient credentials, keys, and tokens are strictly excluded.
    """
    from backend.config import ROOT

    allowed = {
        "PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "SYSTEMROOT",
        "TEMP", "TMP", "USER", "TERM", "SHELL", "HOME", "NODE_PATH",
        "NPM_CONFIG_CACHE", "PYTHONPATH", "PLAYWRIGHT_BROWSERS_PATH",
        # toolchain homes (Azure: /home/tools, deploy/azure/toolchains.py); paths and switches, no secrets
        "JAVA_HOME", "GOROOT", "DOTNET_ROOT", "DOTNET_CLI_TELEMETRY_OPTOUT", "DOTNET_NOLOGO", "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT",
        # Windows: node, npx and Python need these to find programs and their per-user folders; none holds a secret
        "PATHEXT", "COMSPEC", "WINDIR", "APPDATA", "LOCALAPPDATA", "USERPROFILE", "PROGRAMFILES",
    }
    env = {k: v for k, v in os.environ.items() if k in allowed and not SENSITIVE_ENV_PATTERN.search(k)}
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _without_platform(env, ROOT)
    browsers = playwright_browsers()
    if browsers:  # commands may get another HOME (the harness does), so Playwright is told where Chromium really is
        env.setdefault("PLAYWRIGHT_BROWSERS_PATH", browsers)
    if "HOME" not in env:
        env["HOME"] = tempfile.gettempdir()  # every OS has one; "/tmp" is POSIX only

    root_modules = ROOT / "node_modules"
    if root_modules.exists():
        bin_dir = str(root_modules / ".bin")
        current_path = env.get("PATH", "")
        if bin_dir not in current_path:
            env["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"  # ";" on Windows
        env.setdefault("NODE_PATH", str(root_modules))

    if extra_env:
        # Strip any sensitive environment variable before passing to sandbox
        safe_extra = {
            str(k): str(v)
            for k, v in extra_env.items()
            if not SENSITIVE_ENV_PATTERN.search(str(k))
        }
        env.update(safe_extra)
    return env
