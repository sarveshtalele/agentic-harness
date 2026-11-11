"""OpenTelemetry tracing (plan H9): MAF's instrumentation, platform spans, the local span store, and optional OTLP.

Spans: one root per API or chat request (middleware), one per tool call (runtime.tool_audit, same id as its tool_calls row),
one root per background workflow run and one per stage (maf/engine), one per sandbox job (repos/sandbox). MAF adds the agent,
model and tool-execution spans under them. Skill Studio steps are API requests, so each step is its own request span.
"""
from backend.core.tracing.middleware import TraceRequests
from backend.core.tracing.setup import flush, otlp_exporter, setup
from backend.core.tracing.spans import clean, ids, new_root, note, span, traced

__all__ = ["TraceRequests", "clean", "flush", "ids", "new_root", "note", "otlp_exporter", "setup", "span", "traced"]
