"""Durable MAF AG-UI thread snapshots for the harness, so plan/execute mode and pending approvals outlive one request.

`SqliteSnapshotStore` implements MAF's `AGUIThreadSnapshotStore` protocol over `backend.db` (migration 018). The scope is
"<project>/<user>": the platform's authorization boundary, set by the server, never by the client.
"""
from __future__ import annotations

import dataclasses
import json

from agent_framework.ag_ui import AGUIThreadSnapshot
from agent_framework_ag_ui._approval_state import InMemoryAGUIApprovalStateStore
from agent_framework_ag_ui._snapshots import _session_id_for_thread

from backend.core.security import redact
from backend.db import db, now

# MAF keeps which approval interrupts are still answerable in the AgentFrameworkAgent, which the route builds per
# request; one process-wide store lets the approval sent on the next request find its pending call.
# ponytail: process-local, as MAF ships it (1.24 has no durable approval store); after a restart a pending card is retired.
APPROVALS = InMemoryAGUIApprovalStateStore()


def scope(project_id: str, user_id: str) -> str:
    return f"{project_id}/{user_id}"


def session_id(project_id: str, user_id: str, thread_id: str) -> str:
    """The MAF session id the AG-UI layer derives for this scoped thread; todos and memory files are keyed by it."""
    return _session_id_for_thread(scope=scope(project_id, user_id), thread_id=thread_id)


def _redacted(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [_redacted(v) for v in value]
    if isinstance(value, dict):
        return {k: _redacted(v) for k, v in value.items()}
    return value


class SqliteSnapshotStore:
    """MAF `AGUIThreadSnapshotStore`: the latest snapshot per (scope, thread), text redacted before it is stored."""

    async def save(self, *, scope: str, thread_id: str, snapshot: AGUIThreadSnapshot) -> None:
        body = json.dumps(_redacted(dataclasses.asdict(snapshot)))
        with db() as con:
            con.execute("INSERT INTO harness_snapshots (scope, thread_id, body, updated_at) VALUES (?,?,?,?) "
                        "ON CONFLICT(scope, thread_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at", (scope, thread_id, body, now()))

    async def get(self, *, scope: str, thread_id: str) -> AGUIThreadSnapshot | None:
        with db() as con:
            found = con.execute("SELECT body FROM harness_snapshots WHERE scope=? AND thread_id=?", (scope, thread_id)).fetchone()
        return AGUIThreadSnapshot(**json.loads(found["body"])) if found else None

    async def delete(self, *, scope: str, thread_id: str) -> bool:
        with db() as con:
            return con.execute("DELETE FROM harness_snapshots WHERE scope=? AND thread_id=?", (scope, thread_id)).rowcount > 0

    async def clear(self, *, scope: str | None = None) -> None:
        with db() as con:
            if scope is None:
                con.execute("DELETE FROM harness_snapshots")
            else:
                con.execute("DELETE FROM harness_snapshots WHERE scope=?", (scope,))


SNAPSHOTS = SqliteSnapshotStore()
