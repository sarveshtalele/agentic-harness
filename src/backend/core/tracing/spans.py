"""Spans the platform adds beside MAF's own: a span around a block, a new root for background work, and notes on the root.

Every attribute value passes redact() here, and again in the span store, so a secret never reaches a span.
"""
from __future__ import annotations

import functools
import inspect
import json
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

from backend.core.security import redact

MAX_TEXT = 4000
# The run being traced: {"span": root span, "tokens_in": n, "tokens_out": n}. Set by the request middleware and by new_root().
_root: ContextVar[dict | None] = ContextVar("aqe_trace_root", default=None)
FIRST_WINS = {"project_id", "user_id", "agent", "model", "run_id", "thread_id"}  # a sub-agent must not rename the run it runs inside


def tracer():
    return trace.get_tracer("backend")


def clean(value):
    """A value OpenTelemetry accepts, with text redacted and capped."""
    if isinstance(value, (bool, int, float)):
        return value
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return redact(text)[:MAX_TEXT]


def attrs(values: dict) -> dict:
    return {k: clean(v) for k, v in values.items() if v is not None and v != ""}


def failed(span: Span, exc: BaseException) -> None:
    """Status and type only. The stack stays in the errors log, which is admin only."""
    span.set_status(StatusCode.ERROR, redact(str(exc) or type(exc).__name__)[:300])
    span.set_attribute("error_type", type(exc).__name__)


@contextmanager
def span(name: str, **values) -> Iterator[Span]:
    with tracer().start_as_current_span(name, attributes=attrs(values), record_exception=False, set_status_on_exception=False) as current:
        try:
            yield current
        except BaseException as exc:
            failed(current, exc)
            raise


@contextmanager
def new_root(name: str, **values) -> Iterator[Span]:
    """A new trace with no parent, for work that outlives the request that started it (a workflow run)."""
    holder: dict = {k: v for k, v in values.items() if v is not None and v != ""}  # so note() cannot replace them
    token = _root.set(holder)
    try:
        with tracer().start_as_current_span(name, context=otel_context.Context(), attributes=attrs(values), record_exception=False, set_status_on_exception=False) as current:
            holder["span"] = current
            try:
                yield current
            except BaseException as exc:
                failed(current, exc)
                raise
    finally:
        _root.reset(token)


def note(**values) -> None:
    """Facts learned deep inside a run (project, agent, model, tokens, error id) are set on its root span, so the runs list can show them."""
    holder = _root.get()
    root = holder.get("span") if holder else None
    if root is None or not root.is_recording():
        return
    for key, value in values.items():
        if value is None or value == "":
            continue
        if key in ("tokens_in", "tokens_out"):
            holder[key] = holder.get(key, 0) + int(value)
            root.set_attribute(key, holder[key])
        elif key not in FIRST_WINS or key not in holder:
            holder[key] = value
            root.set_attribute(key, clean(value))


def ids(current: Span | None = None) -> tuple[str, str] | None:
    """(trace_id, span_id) as hex, or None when nothing is being traced."""
    found = (current or trace.get_current_span()).get_span_context()
    return (format(found.trace_id, "032x"), format(found.span_id, "016x")) if found.is_valid else None


def traced(name: str, *fields: str):
    """Decorator: one span per call, with the named arguments as attributes. A dict result's "status" is recorded too."""

    def wrap(fn):
        signature = inspect.signature(fn)

        def values(args, kwargs) -> dict:
            bound = signature.bind_partial(*args, **kwargs).arguments
            return {f: bound.get(f) for f in fields}

        def outcome(current: Span, result):
            if isinstance(result, dict) and "status" in result:
                current.set_attribute("outcome", str(result["status"]))
            return result

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def run_async(*args, **kwargs):
                with span(name, **values(args, kwargs)) as current:
                    return outcome(current, await fn(*args, **kwargs))

            return run_async

        @functools.wraps(fn)
        def run(*args, **kwargs):
            with span(name, **values(args, kwargs)) as current:
                return outcome(current, fn(*args, **kwargs))

        return run

    return wrap
