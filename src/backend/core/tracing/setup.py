"""One TracerProvider for the process: the local span store always, OTLP only when OTEL_EXPORTER_OTLP_ENDPOINT is set.

MAF's instrumentation is switched on with sensitive data OFF, so MAF itself puts no message or tool content in spans.
"""
from __future__ import annotations

import os
import threading

from agent_framework.observability import create_resource, enable_instrumentation
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from backend import config
from backend.core.tracing import store

_lock = threading.Lock()
_provider: TracerProvider | None = None


def otlp_exporter() -> SpanExporter | None:
    """The OTLP gRPC exporter reads the endpoint and OTEL_EXPORTER_OTLP_HEADERS from the environment itself. Neither is logged here.

    ponytail: gRPC only (the pinned exporter). Add opentelemetry-exporter-otlp-proto-http when a collector needs http/protobuf.
    """
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter()


def setup() -> TracerProvider:
    """Safe to call more than once (each app start calls it); retention runs every time, the provider is made once."""
    global _provider
    store.prune(config.TRACE_RETENTION_DAYS)
    with _lock:
        if _provider is None:
            provider = TracerProvider(resource=create_resource(service_name=os.environ.get("OTEL_SERVICE_NAME") or "agentic-qe-platform"))
            provider.add_span_processor(BatchSpanProcessor(store.SpanStore()))
            if exporter := otlp_exporter():
                provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            enable_instrumentation(enable_sensitive_data=False)
            _provider = provider
    return _provider


def flush(timeout_ms: int = 5000) -> bool:
    """Writes every finished span now. Tests use it; the app never needs to."""
    return _provider.force_flush(timeout_ms) if _provider else True
