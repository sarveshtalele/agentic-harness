"""Projects bound to a folder on the person's own machine (the `aqh` CLI, docs/PHASE2_PLAN.md section 11.1).

Claude Code edits the files in the folder it was started in, not a copy. In the `cli` profile a project can be bound to
such a folder: the harness then works in that folder directly (no sandbox clone), shells keep the person's real HOME,
and nothing else changes (permissions, hooks, approvals, ledger). The binding is a small JSON file in the data folder.
Only the `cli` profile binds folders: the shared web server and the desktop app keep their sandbox clones.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend import config

FILE = config.DATA_DIR / "cli-workspaces.json"


def _all() -> dict[str, str]:
    try:
        data = json.loads(FILE.read_text(encoding="utf-8")) if FILE.is_file() else {}
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def bind(project_id: str, folder: str) -> Path:
    if config.PROFILE != "cli":
        raise PermissionError("Folders are bound only by the aqh CLI (ATLAS_PROFILE=cli)")
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Not a folder: {path}")
    data = _all()
    data[project_id] = str(path)
    FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return path


def path_of(project_id: str) -> Path | None:
    if config.PROFILE != "cli":
        return None
    found = _all().get(project_id)
    return Path(found) if found and Path(found).is_dir() else None


def project_for(folder: str) -> str | None:
    """The project already bound to this folder, if any."""
    wanted = str(Path(folder).expanduser().resolve())
    return next((pid for pid, path in _all().items() if path == wanted), None)
