"""Slash commands the platform answers itself, without the model or plugin prompt hooks: `/mode` and `/rewind`."""
from __future__ import annotations

from backend.core import auth
from backend.maf import harness
from backend.maf.harness_kit import checkpoints, permissions, workspace


def answer(project_id: str, thread_id: str, name: str, arg: str | None) -> str:
    """`/mode [name]` and `/rewind [n]`: answered by the platform, not the model."""
    user_id = auth.acting_user(project_id)
    tools_dir = harness.state_dirs(project_id, user_id)["tools"]
    if name == "mode":
        return (permissions.set_mode(tools_dir, thread_id, arg) if arg else
                f"Permission mode for this conversation: {permissions.get_mode(tools_dir, thread_id)}. Modes: {', '.join(permissions.MODES)}.")
    ws = workspace.open_workspace(project_id, thread_id, user_id)
    if ws is None:
        return "Nothing to rewind: this project has no repository."
    store = checkpoints.folder(tools_dir, thread_id)
    if not arg:
        return checkpoints.listing(store)
    return checkpoints.rewind(ws, store, int(arg)) if arg.isdigit() else "Use /rewind to list turns, then /rewind <number>."
