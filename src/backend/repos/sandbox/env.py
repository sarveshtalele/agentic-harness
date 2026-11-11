"""Zero-trust environment allowlist for sandbox subprocesses."""
from __future__ import annotations

import os
import re


SENSITIVE_ENV_PATTERN = re.compile(
    r"(?i)(key|secret|token|password|passwd|auth|cred|atlas|openai|anthropic|aws|github|bearer|private)"
)


def clean_sandbox_env(extra_env: dict | None = None) -> dict:
    """Zero-trust allowlist of environment variables for isolated subprocess executions.
    Ambient credentials, keys, and tokens are strictly excluded.
    """
    from backend.config import ROOT

    allowed = {
        "PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "SYSTEMROOT",
        "TEMP", "TMP", "USER", "TERM", "SHELL", "HOME", "NODE_PATH",
        "NPM_CONFIG_CACHE", "PYTHONPATH"
    }
    env = {k: v for k, v in os.environ.items() if k in allowed and not SENSITIVE_ENV_PATTERN.search(k)}
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if "HOME" not in env:
        env["HOME"] = "/tmp"

    root_modules = ROOT / "node_modules"
    if root_modules.exists():
        bin_dir = str(root_modules / ".bin")
        current_path = env.get("PATH", "")
        if bin_dir not in current_path:
            env["PATH"] = f"{bin_dir}:{current_path}"
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
