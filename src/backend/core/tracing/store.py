"""The local span store: a SpanExporter that writes finished spans to the `spans` table, and retention."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

from backend.core.tracing.spans import clean
from backend.db import db

INSERT = ("INSERT OR REPLACE INTO spans (span_id, trace_id, parent_id, name, kind, started_at, ended_at, duration_ms, status, attributes, project_id, user_id, root)"
          " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)")
MAX_ATTRIBUTES = 16000  # characters of attribute JSON kept per span


def stamp(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, timezone.utc).isoformat(timespec="milliseconds")


def _attributes(span: ReadableSpan) -> dict:
    """Every value redacted again here: MAF's own spans did not pass through spans.clean()."""
    found = {k: (list(map(clean, v)) if isinstance(v, (list, tuple)) else clean(v)) for k, v in (span.attributes or {}).items()}
    for event in span.events or ():
        if event.name == "exception":  # type and message only, never the stack trace
            found.setdefault("exception.type", clean((event.attributes or {}).get("exception.type", "")))
            found.setdefault("exception.message", clean((event.attributes or {}).get("exception.message", ""))[:300])
    if span.status.status_code == StatusCode.ERROR and span.status.description:
        found.setdefault("error", clean(span.status.description))
    return found


def _row(span: ReadableSpan) -> tuple:
    found = _attributes(span)
    text = json.dumps(found, default=str)
    if len(text) > MAX_ATTRIBUTES:
        found = {k: (v[:500] if isinstance(v, str) else v) for k, v in found.items()}
        found["truncated"] = True
        text = json.dumps(found, default=str)
    error = span.status.status_code == StatusCode.ERROR or found.get("status") == "error"
    parent = format(span.parent.span_id, "016x") if span.parent else None
    return (format(span.context.span_id, "016x"), format(span.context.trace_id, "032x"), parent, span.name, span.kind.name.lower(),
            stamp(span.start_time), stamp(span.end_time), round((span.end_time - span.start_time) / 1e6), "error" if error else "ok", text,
            found.get("project_id") or None, found.get("user_id") or None, int(parent is None))


class SpanStore(SpanExporter):
    """Runs on the BatchSpanProcessor's thread, so a request never waits for this write."""

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            with db() as con:
                con.executemany(INSERT, [_row(s) for s in spans if s.end_time])
        except Exception:  # noqa: BLE001 - a lost span must never break the app; the span content is never logged
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None


def prune(keep_days: int, now: datetime | None = None) -> int:
    """Deletes spans that started more than keep_days ago. Returns how many."""
    oldest = ((now or datetime.now(timezone.utc)) - timedelta(days=keep_days)).isoformat(timespec="milliseconds")
    with db() as con:
        return con.execute("DELETE FROM spans WHERE started_at < ?", (oldest,)).rowcount
