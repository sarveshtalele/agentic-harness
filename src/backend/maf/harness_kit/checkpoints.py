"""File checkpoints and `/rewind` (docs/PHASE2_PLAN.md section 10), as in Claude Code.

Before the harness writes, edits or deletes a file, the file's current content (or the fact that it did not exist) is
saved under the conversation and the turn: `<harness>/<project>/checkpoints/<thread>/<turn>/NNN.json`. `/rewind` lists
recent turns with the files each changed; `/rewind <n>` puts every file changed in turn n and later back to how it was
before turn n, and records that in the ledger. Changes a shell command makes are not captured (Claude Code's limit too).
Paths are workspace-relative and go through `safe_path` on the way back.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from agent_framework import FunctionInvocationContext, function_middleware
from pydantic import BaseModel

from backend.core import ledger
from backend.core.security import safe_path

CHANGES = frozenset({"file_access_write", "file_access_replace", "file_access_replace_lines", "file_access_delete"})
SHOWN = 10


def folder(state_dir: Path, thread_id: str) -> Path:
    return state_dir.parent / "checkpoints" / thread_id


def new_turn() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + f"-{time.monotonic_ns() % 1_000_000:06d}"


def save(ws, store: Path, turn: str, relative: str) -> None:
    target = safe_path(ws.root, relative)
    turn_dir = store / turn
    turn_dir.mkdir(parents=True, exist_ok=True)
    if any(json.loads(p.read_text(encoding="utf-8"))["path"] == relative for p in turn_dir.glob("*.json")):
        return  # the first snapshot in a turn is the state before it
    existed = target.is_file()
    record = {"path": relative, "existed": existed, "content": target.read_text(encoding="utf-8", errors="surrogateescape") if existed else ""}
    (turn_dir / f"{len(list(turn_dir.glob('*.json'))):03d}.json").write_text(json.dumps(record), encoding="utf-8")


def checkpoint(ws, store: Path, turn: str):
    """Function middleware: snapshot a file right before a harness tool changes it."""

    @function_middleware
    async def snapshot(context: FunctionInvocationContext, call_next) -> None:
        if context.function.name in CHANGES:
            args = context.arguments.model_dump() if isinstance(context.arguments, BaseModel) else dict(context.arguments or {})
            if relative := str(args.get("file_name") or ""):
                try:
                    save(ws, store, turn, relative)
                except (OSError, ValueError, UnicodeDecodeError):
                    pass  # a path safe_path refuses is refused by the tool itself; a binary file is not snapshotted
        await call_next()

    return snapshot


def turns(store: Path) -> list[tuple[str, list[str]]]:
    if not store.is_dir():
        return []
    found = []
    for turn_dir in sorted(p for p in store.iterdir() if p.is_dir()):
        paths = [json.loads(p.read_text(encoding="utf-8"))["path"] for p in sorted(turn_dir.glob("*.json"))]
        if paths:
            found.append((turn_dir.name, paths))
    return found


def listing(store: Path) -> str:
    found = turns(store)[-SHOWN:]
    if not found:
        return "Nothing to rewind: the harness has not changed a file in this conversation yet (shell commands are not tracked)."
    lines = [f"{i}. {name[9:11]}:{name[11:13]}:{name[13:15]} on {name[:4]}-{name[4:6]}-{name[6:8]}: {', '.join(paths[:5])}"
             + (f" and {len(paths) - 5} more" if len(paths) > 5 else "") for i, (name, paths) in enumerate(found, 1)]
    return "Turns that changed files (send /rewind <number> to put those files back as they were before that turn):\n" + "\n".join(lines)


def rewind(ws, store: Path, number: int) -> str:
    found = turns(store)[-SHOWN:]
    if not 1 <= number <= len(found):
        return f"There is no turn {number}. " + listing(store)
    chosen = [name for name, _ in found[number - 1:]]
    restored: dict[str, dict] = {}
    for name in reversed(chosen):  # oldest snapshot last, so each file ends at its state before the chosen turn
        for record_file in sorted((store / name).glob("*.json")):
            record = json.loads(record_file.read_text(encoding="utf-8"))
            restored[record["path"]] = record
    for relative, record in restored.items():
        target = safe_path(ws.root, relative)
        if record["existed"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(record["content"], encoding="utf-8", errors="surrogateescape")
        elif target.is_file():
            target.unlink()  # the file did not exist before that turn
    ledger.append(ws.project_id, f"user:{ws.user_id}", "harness.rewind", ws.thread_id, {"from_turn": chosen[0], "files": sorted(restored)})
    return f"Rewound {len(restored)} file(s) to before turn {number}: {', '.join(sorted(restored))}. The conversation itself is unchanged."
