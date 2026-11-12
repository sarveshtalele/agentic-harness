"""aqh settings (docs/PHASE2_PLAN.md section 17, D-CLI): the model proxy's base URL, model name and key.

Sources, first found wins: CLI flags > the project's `.aqh/settings.json` > `~/.aqh/settings.json` > the environment.
A settings file holds `{"model": {"baseUrl": ..., "name": ...}, "env": {"OPENAI_BASE_URL": ..., "DEFAULT_MODEL": ...}}`.
The key: `OPENAI_API_KEY` in the environment, or in a settings file's `env` block, or the OS keychain (macOS Keychain,
Windows Credential Manager, Linux Secret Service) after `aqh config set-key`. It is never printed or logged; `aqh doctor`
names its source only. `~/.aqh` is created owner-only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SERVICE = "agentic-qe-harness"


def home() -> Path:
    folder = Path(os.environ.get("AQH_HOME") or Path.home() / ".aqh")
    folder.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        folder.chmod(0o700)
    return folder


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def layers(cwd: Path | None = None) -> list[tuple[str, dict]]:
    cwd = cwd or Path.cwd()
    return [("project .aqh/settings.json", _read(cwd / ".aqh" / "settings.json")), ("~/.aqh/settings.json", _read(home() / "settings.json"))]


def model(overrides: dict | None = None, cwd: Path | None = None) -> dict:
    """{"base_url", "name", "api_key", "sources": {field: source name}}; never prints the key."""
    out, sources = {}, {}
    wanted = {"base_url": ("baseUrl", "OPENAI_BASE_URL"), "name": ("name", "DEFAULT_MODEL"), "api_key": (None, "OPENAI_API_KEY")}
    for field, value in (overrides or {}).items():
        if value:
            out[field], sources[field] = value, "command line"
    for source, data in layers(cwd):
        block, env = data.get("model") or {}, data.get("env") or {}
        for field, (key, env_key) in wanted.items():
            if field in out:
                continue
            value = (block.get(key) if key else None) or env.get(env_key)
            if value:
                out[field], sources[field] = str(value), source
    for field, (_, env_key) in wanted.items():
        if field not in out and os.environ.get(env_key):
            out[field], sources[field] = os.environ[env_key], f"environment {env_key}"
    if "api_key" not in out and (stored := keychain_get()):
        out["api_key"], sources["api_key"] = stored, "OS keychain"
    return {**out, "sources": sources}


def keychain_get() -> str | None:
    try:
        import keyring

        return keyring.get_password(SERVICE, "model-api-key")
    except Exception:  # noqa: BLE001 - no keychain backend on this machine: the key must come from the environment
        return None


def keychain_set(value: str) -> None:
    import keyring

    keyring.set_password(SERVICE, "model-api-key", value)


def save_model(base_url: str | None, name: str | None) -> Path:
    path = home() / "settings.json"
    data = _read(path)
    block = data.setdefault("model", {})
    if base_url:
        block["baseUrl"] = base_url.rstrip("/")
    if name:
        block["name"] = name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)
    return path
