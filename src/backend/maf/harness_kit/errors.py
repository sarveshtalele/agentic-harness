"""One error shape for a failed harness tool call (FINAL_PLAN 5.5): {code, message, action, retryable, trace_id}.

A tool that raises is still recorded as an error by `tool_audit` (it sits inside this middleware). The model then reads
the same short shaped text the user sees, with the action to take, instead of a bare exception string, so it can tell
a retryable timeout from a wrong argument. Model call retries are the client's (`MODEL_RETRIES`); this covers tools,
MCP servers, the sandbox and the database as tools reach them.
"""
from __future__ import annotations

import json

from agent_framework import FunctionInvocationContext, MiddlewareTermination, function_middleware
from pydantic import ValidationError

from backend.core import tracing
from backend.core.security import redact

# (code, retryable, action) by exception type name or base class; the first match wins
RULES = [
    ((TimeoutError,), "timeout", True, "Retry once; if it times out again, narrow the call (a smaller range, a shorter command)."),
    ((PermissionError,), "permission", False, "Do not retry. The path or action is outside what this session may do."),
    ((FileNotFoundError, IsADirectoryError, NotADirectoryError), "not_found", False, "Check the path with file_access_ls, then call again with the right one."),
    ((ValidationError, TypeError, ValueError, KeyError), "invalid_arguments", False, "Fix the arguments to match the tool's parameters, then call again."),
    ((ConnectionError,), "unavailable", True, "Retry once; if it still fails, tell the user the service is not reachable."),
]
NAMED = {"DatabaseNotConfigured": ("database", False, "Stop and tell the user: PostgreSQL is not reachable (run `python scripts/dev.py db`)."),
         "OperationalError": ("database", True, "Retry once; if it still fails, tell the user the database is not reachable."),
         "McpError": ("mcp", True, "Retry once; if the MCP server still fails, tell the user which server and what it said.")}


def shape(exc: BaseException) -> dict:
    code, retryable, action = next(((c, r, a) for types, c, r, a in RULES if isinstance(exc, types)),
                                   NAMED.get(type(exc).__name__, ("tool_error", False, "Do not repeat the same call; change the approach or tell the user.")))
    found = tracing.ids()
    return {"code": code, "message": redact(str(exc) or type(exc).__name__)[:600], "action": action, "retryable": retryable,
            "trace_id": found[0] if found else ""}


def error_shape():
    @function_middleware
    async def shaped(context: FunctionInvocationContext, call_next) -> None:
        try:
            await call_next()
        except MiddlewareTermination:
            raise
        except Exception as exc:  # noqa: BLE001 - every tool failure becomes the one shape
            found = shape(exc)
            context.result = f"Error [{found['code']}]: " + json.dumps(found)

    return shaped
