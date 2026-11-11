"""H9 span store: retention deletes only old spans, attributes are redacted on write, and OTLP exists only with its endpoint set."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from backend.core import tracing
from backend.core.tracing import store
from backend.db import db, new_id

SECRET = "sk-" + "Tq7Vb3Kd9Wm2" * 3  # built at run time so no secret-shaped literal sits in the repository


def _insert(started: datetime) -> str:
    span_id = new_id("sp")
    stamp = started.isoformat(timespec="milliseconds")
    with db() as con:
        con.execute("INSERT INTO spans (span_id, trace_id, name, kind, started_at, ended_at, duration_ms, status, root) VALUES (?,?,?,?,?,?,?,?,1)",
                    (span_id, new_id("tr"), "GET /api/projects", "server", stamp, stamp, 1, "ok"))
    return span_id


def _exists(span_id: str) -> bool:
    with db() as con:
        return con.execute("SELECT 1 FROM spans WHERE span_id=?", (span_id,)).fetchone() is not None


def test_retention_deletes_only_spans_older_than_the_limit():
    now = datetime.now(timezone.utc)
    old, edge, fresh = _insert(now - timedelta(days=31)), _insert(now - timedelta(days=29)), _insert(now)
    assert store.prune(30, now) >= 1
    assert not _exists(old) and _exists(edge) and _exists(fresh)


def test_the_exporter_redacts_every_attribute_it_writes():
    tracing.setup()
    with tracing.new_root("workflow qe") as root:
        root.set_attribute("raw", f"token {SECRET}")  # set directly, as MAF's own spans do, so only the store's redaction stands between it and disk
        with tracing.span("tool run_tests", input={"api_key": SECRET}):
            pass
    tracing.flush()
    with db() as con:
        stored = [json.loads(r[0]) for r in con.execute("SELECT attributes FROM spans WHERE trace_id=?", (tracing.ids(root)[0],))]
    assert len(stored) == 2
    text = json.dumps(stored)
    assert SECRET not in text and "token" in text


def test_the_otlp_exporter_exists_only_when_its_endpoint_is_set(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert tracing.otlp_exporter() is None
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    assert isinstance(tracing.otlp_exporter(), OTLPSpanExporter)  # constructing it opens no connection
