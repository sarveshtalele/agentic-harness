"""Background execution of a run: its task, checkpoint storage, event consumption, approvals and final status."""
from __future__ import annotations

import asyncio
import json

from agent_framework import FileCheckpointStorage

from backend.config import CHECKPOINTS
from backend.core import ledger
from backend.core.security import redact
from backend.db import db, now
from backend.maf.engine.failures import _failures, record_failure
from backend.maf.engine.run_context import add_event
from backend.maf.engine.stages import _public_state
from backend.maf.engine.specs import ApprovalRequest

_tasks: set[asyncio.Task] = set()
_active: dict[str, asyncio.Task] = {}


def _storage(run_id: str) -> FileCheckpointStorage:
    folder = CHECKPOINTS / run_id
    folder.mkdir(parents=True, exist_ok=True)
    return FileCheckpointStorage(folder, allowed_checkpoint_types=["backend.maf.engine:ApprovalRequest"])


async def _consume(run_id: str, project_id: str, stream) -> None:
    pending: list = []
    output = None
    async for event in stream:
        if event.type == "request_info":
            pending.append(event)
        elif event.type == "output":
            output = event.data
        elif event.type == "failed":
            raise RuntimeError(str(event.details))
    if pending:
        for event in pending:
            _register_approval(run_id, project_id, event)
        _finish(run_id, "waiting_approval")
    else:
        state = json.loads(output) if isinstance(output, str) else {}
        with db() as con:
            con.execute("UPDATE runs SET state=? WHERE id=?", (json.dumps(_public_state(state), default=str), run_id))
        _finish(run_id, "rejected" if state.get("rejected") else "completed")


def _register_approval(run_id: str, project_id: str, event) -> None:
    data: ApprovalRequest = event.data
    with db() as con:
        con.execute(
            "INSERT OR REPLACE INTO approvals (id, run_id, project_id, gate, title, summary, payload, status, created_at) VALUES (?,?,?,?,?,?,?,'pending',?)",
            (event.request_id, run_id, project_id, data.gate if data.gate >= 0 else None, data.title, data.summary, data.payload, now()),
        )
    add_event(run_id, "approval_required", data.stage, data.title, {"approval_id": event.request_id, "gate": data.gate})


def _finish(run_id: str, status: str, error: str = "") -> None:
    terminal = status in {"completed", "failed", "rejected", "interrupted", "cancelled"}
    with db() as con:
        con.execute("UPDATE runs SET status=?, error=?, ended_at=? WHERE id=?", (status, redact(error), now() if terminal else None, run_id))
        project_id = con.execute("SELECT project_id FROM runs WHERE id=?", (run_id,)).fetchone()["project_id"]
    add_event(run_id, "status", "", status, {"error": redact(error)} if error else None)
    ledger.append(project_id, "system", f"run.{status}", run_id, {"error": redact(error)[:400]} if error else {})


async def _guarded(run_id: str, project_id: str, stream) -> None:
    try:
        await _consume(run_id, project_id, stream)
    except asyncio.CancelledError:
        _finish(run_id, "cancelled")
        raise
    except Exception as exc:  # recorded in run_failures with a redacted stack, then shown on the run
        failure = _failures.pop(run_id, None) or record_failure(run_id, "", exc)
        _finish(run_id, "failed", f"{failure['stage']}: {failure['message']}" if failure["stage"] else failure["message"])


def _spawn(run_id: str, coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    _active[run_id] = task
    task.add_done_callback(_tasks.discard)
    return task

