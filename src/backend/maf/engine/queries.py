"""Reading runs: who holds the slot, the run with its approvals and failure, its events, and restart recovery."""
from __future__ import annotations

import json

from backend.db import db, now, row, rows


ACTIVE = ("running", "waiting_approval")  # a waiting run still holds its worktree, so it keeps the slot


class RunActive(ValueError):
    """Another run of this kind is in progress in this project. Names it, and where to open it."""

    def __init__(self, project_id: str, workflow: str):
        with db() as con:
            found = row(con.execute("SELECT id, status, started_at FROM runs WHERE project_id=? AND workflow=? AND status IN ('running','waiting_approval') ORDER BY started_at LIMIT 1", (project_id, workflow))) or {}
        self.run_id = found.get("id", "")
        super().__init__(f"A {workflow} run is already {found.get('status', 'in progress').replace('_', ' ')} in this project: {self.run_id}, started {found.get('started_at', '')}. "
                         f"Open it at /projects/{project_id}/runs/{self.run_id}, and finish or cancel it before starting another.")


def recover() -> None:
    """Tasks do not survive a restart. Waiting runs are safe on their checkpoint; running ones are not."""
    with db() as con:
        for item in rows(con.execute("SELECT id FROM runs WHERE status='running'")):
            con.execute("UPDATE runs SET status='interrupted', error='Application restarted during this run', ended_at=? WHERE id=?", (now(), item["id"]))


def get(run_id: str) -> dict:
    with db() as con:
        found = row(con.execute("SELECT * FROM runs WHERE id=?", (run_id,)))
        if not found:
            raise KeyError(run_id)
        found["approvals"] = rows(con.execute("SELECT * FROM approvals WHERE run_id=? ORDER BY created_at", (run_id,)))
    for key in ("input", "state"):
        found[key] = json.loads(found[key])
    with db() as con:
        found["failure"] = row(con.execute("SELECT * FROM run_failures WHERE run_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1", (run_id,)))
    for approval in found["approvals"]:
        approval["payload"] = json.loads(approval["payload"])
    return found


def events(run_id: str, after: int = 0) -> list[dict]:
    with db() as con:
        items = rows(con.execute("SELECT * FROM run_events WHERE run_id=? AND seq>? ORDER BY seq", (run_id, after)))
    for item in items:
        item["data"] = json.loads(item["data"])
    return items
