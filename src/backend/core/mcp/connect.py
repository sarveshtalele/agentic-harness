"""Open real MCP sessions through MAF: connect and list tools, or call one tool. Every session is closed afterwards."""
from __future__ import annotations

import asyncio
import json
import time

from agent_framework import MCPStdioTool, MCPStreamableHTTPTool, MCPWebsocketTool

from backend.core.mcp import grants, registry
from backend.core.mcp.registry import McpProblem
from backend.core.security import redact
from backend.db import db
from backend.repos.sandbox import clean_sandbox_env

DEFAULT_TIMEOUT = 60
TIMEOUT_KEY = "mcp_timeout_seconds"  # settings table; seconds for one whole connect or call


def timeout_seconds() -> int:
    with db() as con:
        found = con.execute("SELECT value FROM settings WHERE key=?", (TIMEOUT_KEY,)).fetchone()
    try:
        return max(1, int(found[0])) if found else DEFAULT_TIMEOUT
    except ValueError:
        return DEFAULT_TIMEOUT


def build(server: dict, allowed: list[str] | None = None):
    """An unconnected MAF MCP tool for a server row. stdio gets the clean sandbox env plus the server's own env."""
    common = {"name": server["id"], "load_prompts": False, "request_timeout": timeout_seconds(), "allowed_tools": allowed, "description": server["name"]}
    if server["transport"] == "stdio":
        registry.require_stdio_allowed()
        env = {**clean_sandbox_env(), **registry.secrets(server)}  # the server's own env is set by the admin on purpose
        return MCPStdioTool(command=registry.resolve_command(server["command"]), args=json.loads(server["args"] or "[]"), env=env, **common)
    if server["transport"] == "websocket":
        return MCPWebsocketTool(url=server["url"], **common)
    return MCPStreamableHTTPTool(url=server["url"], static_headers=registry.secrets(server) or None, **common)


def _message(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return f"No answer within {timeout_seconds()} s"
    first = exc.args[0] if exc.args and isinstance(exc.args[0], str) else str(exc)
    cause = exc.__cause__
    while isinstance(cause, BaseExceptionGroup) and cause.exceptions:
        cause = cause.exceptions[0]
    detail = f": {cause}" if cause and str(cause) not in first else ""
    return redact(f"{first}{detail}" or type(exc).__name__)


async def connect(server_id: str) -> dict:
    """Open a session, list the tools, store exactly those, close. Any failure stores `error` and no tools."""
    server = registry.get(server_id)
    if server["transport"] == "stdio":
        registry.require_stdio_allowed()
    try:
        tool = build(server)
        async with asyncio.timeout(timeout_seconds()):
            async with tool:
                listed = [{"name": (f.additional_properties or {}).get("_mcp_remote_name", f.name), "description": f.description or "",
                           "input_schema": f.parameters()} for f in tool.functions]
    except Exception as exc:  # noqa: BLE001 - every failure becomes the stored error, never invented tools
        registry.mark_error(server_id, exc.message if isinstance(exc, McpProblem) else _message(exc))
        return registry.get(server_id)
    registry.store_tools(server_id, listed)
    return registry.get(server_id)


def _contents(result) -> list[dict]:
    items = result if isinstance(result, list) else [result]
    out = []
    for item in items:
        if isinstance(item, str):
            out.append({"type": "text", "text": item})
            continue
        data = item.to_dict()
        data.pop("additional_properties", None)
        out.append(data)
    return out


async def call(server_id: str, tool_name: str, arguments: dict, user: dict) -> dict:
    """Call one granted tool of a connected server. Returns the server's real result and the latency."""
    server = registry.get(server_id)
    if server["status"] != registry.CONNECTED:
        raise McpProblem(409, "Connect this server first: its tools are known only after a real connection")
    if tool_name not in {t["name"] for t in registry.tools(server_id)}:
        raise KeyError(f"tool {tool_name} on {server_id}")
    if not grants.allows(server_id, tool_name, user):
        raise McpProblem(403, f"The tool {tool_name} is not granted to your role. Ask an administrator")
    if server["transport"] == "stdio":
        registry.require_stdio_allowed()
    if "tool_name" in arguments:
        raise McpProblem(400, "An argument may not be named tool_name")  # ponytail: MAF's call_tool takes tool_name positionally
    started = time.monotonic()
    tool = build(server, allowed=[tool_name])
    try:
        async with asyncio.timeout(timeout_seconds()):
            async with tool:
                result = await tool.call_tool(tool_name, **arguments)
    except McpProblem:
        raise
    except Exception as exc:  # noqa: BLE001 - reported as the call's error
        return {"ok": False, "error": _message(exc), "latency_ms": int((time.monotonic() - started) * 1000), "content": []}
    return {"ok": True, "error": "", "latency_ms": int((time.monotonic() - started) * 1000), "content": _contents(result)}
