"""RunContext, the handle a stage uses to log, emit and keep finished batches, and the run event writer."""
from __future__ import annotations

import hashlib
import json
import shutil

from backend.config import RUNS
from backend.core.security import redact, safe_path
from backend.db import db, now


class RunContext:
    def __init__(self, run_id: str, project_id: str, stage: str = ""):
        self.run_id, self.project_id, self.stage = run_id, project_id, stage

    def log(self, message: str, data: dict | None = None, kind: str = "log") -> None:
        add_event(self.run_id, kind, self.stage, message, data)

    def emit(self, kind: str, message: str, data: dict | None = None) -> None:
        add_event(self.run_id, kind, self.stage, message, data)

    def _part(self, key: str):
        return safe_path(RUNS / self.run_id, f"parts/{self.stage}/{key}.json", for_write=True)

    def keep(self, key: str, data) -> None:
        """Save one finished batch as it completes, so a retry of this stage repeats only what is missing."""
        path = self._part(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(redact(json.dumps(data, default=str)), encoding="utf-8")

    def kept(self, key: str):
        path = self._part(key)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None  # nothing saved, or unreadable: the batch is simply done again

    def clear_parts(self) -> None:
        shutil.rmtree(safe_path(RUNS / self.run_id, f"parts/{self.stage}", for_write=True), ignore_errors=True)

    def earlier_failures(self) -> int:
        """Failures of this stage since it last finished, so an old failure does not shorten a later rework."""
        with db() as con:
            return con.execute(
                """SELECT COUNT(*) FROM run_events WHERE run_id=? AND stage=? AND type='error'
                   AND seq > COALESCE((SELECT MAX(seq) FROM run_events WHERE run_id=? AND stage=? AND type='stage_end'), 0)""",
                (self.run_id, self.stage, self.run_id, self.stage)).fetchone()[0]


def part_key(*inputs) -> str:
    """Names a batch by what it was asked, so a changed request never reuses an old result."""
    return hashlib.sha256(json.dumps(inputs, default=str, sort_keys=True).encode()).hexdigest()[:16]


def add_event(run_id: str, kind: str, stage: str, message: str, data: dict | None = None) -> None:
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        seq = con.execute("SELECT COALESCE(MAX(seq),0)+1 FROM run_events WHERE run_id=?", (run_id,)).fetchone()[0]
        con.execute("INSERT INTO run_events VALUES (?,?,?,?,?,?,?)", (run_id, seq, kind, stage, redact(message), _event_data(data), now()))


def _event_data(data: dict | None) -> str:
    """Event data passes through the same redact() as the message. Should masking ever break the JSON, each string is masked on its own instead."""
    text = json.dumps(data or {}, default=str)
    try:
        return json.dumps(json.loads(redact(text)))
    except ValueError:
        return json.dumps(_masked(json.loads(text)))


def _masked(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _masked(v) for k, v in value.items()}
    return [_masked(v) for v in value] if isinstance(value, list) else value
