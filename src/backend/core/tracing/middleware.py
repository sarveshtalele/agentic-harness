"""ASGI middleware: one root span per API or chat request, named by its route template, never the raw path with ids.

Pure ASGI, so a streamed chat reply stays inside its span until the last byte is sent.
A client's traceparent header is not trusted: every request starts a new trace.
"""
from __future__ import annotations

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import SpanKind, StatusCode
from starlette.routing import Match

from backend.core.tracing.spans import _root, tracer

TRACED = ("/api/", "/agui/")


def _template(scope) -> str:
    """The matched route's template; a request refused before routing is matched here against the same routes."""
    route = scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    app = scope.get("app")
    for candidate in getattr(getattr(app, "router", None), "routes", []):
        match, _ = candidate.matches(scope)
        if match == Match.FULL and getattr(candidate, "path", None):
            return candidate.path
    return "unmatched"


class TraceRequests:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(TRACED):
            return await self.app(scope, receive, send)
        method = scope["method"]
        span = tracer().start_span(f"{method} request", kind=SpanKind.SERVER, context=otel_context.Context(), attributes={"http.request.method": method})
        holder = {"span": span}
        root_token = _root.set(holder)
        context_token = otel_context.attach(trace.set_span_in_context(span))
        status = {"code": 500}

        async def sending(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, sending)
        except BaseException as exc:
            span.set_attribute("error_type", type(exc).__name__)
            raise
        finally:
            template = _template(scope)
            state = scope.get("state") or {}
            span.update_name(f"{method} {template}")
            span.set_attribute("http.route", template)
            span.set_attribute("http.response.status_code", status["code"])
            for key in ("request_id", "user_id"):  # the signed-in account owns the trace, whatever a note said
                if state.get(key):
                    span.set_attribute(key, str(state[key]))
            if (project_id := (scope.get("path_params") or {}).get("project_id")) and "project_id" not in holder:
                span.set_attribute("project_id", str(project_id))
            if status["code"] >= 500 or holder.get("status") == "error":
                span.set_status(StatusCode.ERROR)
                span.set_attribute("status", "error")
            span.end()
            otel_context.detach(context_token)
            _root.reset(root_token)
