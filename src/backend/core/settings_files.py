"""Claude Code-style settings files for the harness (docs/PHASE2_PLAN.md section 9.4).

Layers, highest first: managed (the organisation's file), the person's own, then the project's local and shared files.
- managed: macOS /Library/Application Support/AgenticQE/managed-settings.json, Windows %ProgramData%\\AgenticQE\\
  managed-settings.json, Linux /etc/agentic-qe/managed-settings.json;
- user (not on the shared web server): ~/.aqh/settings.json, then ~/.claude/settings.json (read only, so a Claude Code
  user's own rules carry over);
- project local: .claude/settings.local.json; project shared: .claude/settings.json and .aqh/settings.json.
Managed and user layers are trusted. Project files are repository content (CLAUDE.md): until a folder can be marked
trusted (the CLI, plan step 6) they may only tighten things, so their `deny` and `ask` rules apply and their `allow`
rules, `env` and `hooks` are ignored. Keys read today: `permissions` (allow, ask, deny), `hooks` (Claude Code's shape).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from backend import config


@dataclass
class Layer:
    name: str  # managed, user, project-local, project
    path: Path
    trusted: bool
    data: dict


def managed_path() -> Path:
    if sys.platform == "darwin":
        return Path("/Library/Application Support/AgenticQE/managed-settings.json")
    if os.name == "nt":
        return Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "AgenticQE" / "managed-settings.json"
    return Path("/etc/agentic-qe/managed-settings.json")


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def layers(root=None) -> list[Layer]:
    """Every settings file that exists, highest precedence first."""
    found = [("managed", managed_path(), True)]
    if config.PROFILE != "web":
        found += [("user", Path.home() / ".aqh" / "settings.json", True), ("user", Path.home() / ".claude" / "settings.json", True)]
    if root is not None:
        found += [("project-local", Path(root) / ".claude" / "settings.local.json", False),
                  ("project", Path(root) / ".claude" / "settings.json", False), ("project", Path(root) / ".aqh" / "settings.json", False)]
    return [Layer(name, path, trusted, data) for name, path, trusted in found if (data := _read(path)) is not None]


def permission_rules(root=None) -> dict[str, list[str]]:
    rules = {"allow": [], "ask": [], "deny": []}
    for layer in layers(root):
        block = layer.data.get("permissions") if isinstance(layer.data.get("permissions"), dict) else {}
        for kind in ("deny", "ask") + (("allow",) if layer.trusted else ()):
            rules[kind] += [r for r in block.get(kind, []) if isinstance(r, str)]
    return rules


def hooks(event: str, root=None) -> list[tuple[Layer, dict]]:
    """(layer, hook) for `event` from the trusted layers, as {"matcher": ..., "hook": {...}} pairs flattened."""
    out = []
    for layer in layers(root):
        if not layer.trusted:
            continue  # project hooks would run repository code: only after the folder is trusted (plan step 6)
        groups = (layer.data.get("hooks") or {}).get(event) if isinstance(layer.data.get("hooks"), dict) else None
        for group in groups or []:
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                if isinstance(hook, dict) and hook.get("type") in ("command", "http"):
                    out.append((layer, {**hook, "_matcher": str(group.get("matcher") or "")}))
    return out
