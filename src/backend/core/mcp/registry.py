"""MCP server registry: rows in mcp_servers, secrets encrypted at rest, tools only from a real list_tools.

Secrets are env values (stdio) or header values (http). They are encrypted with core.security, registered with the
log mask, and never returned: callers see only their names.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import urlparse

from backend import config
from backend.core.security import decrypt, encrypt, redact, register_secret
from backend.db import db, new_id, now, row, rows

NOT_CONNECTED, CONNECTED, ERROR = "not_connected", "connected", "error"
TRANSPORTS = ("stdio", "http", "websocket")
STDIO_COMMANDS = {"npx", "node", "uvx", "python", "python3"}
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
STDIO_PROFILES = ("local",)  # stdio servers start a process on this machine: local development only


class McpProblem(Exception):
    """A refusal with the HTTP status the API answers with."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def stdio_allowed() -> bool:
    return config.PROFILE in STDIO_PROFILES


def require_stdio_allowed() -> None:
    if not stdio_allowed():
        raise McpProblem(403, "stdio MCP servers run only in local development; on the web use an HTTP or WebSocket server")


def _check_command(command: str, args: list) -> None:
    if not command or any(c in command for c in "\n\r\x00"):
        raise McpProblem(400, "A stdio server needs a command")
    if command not in STDIO_COMMANDS and not (Path(command).is_absolute() and Path(command).is_file()):
        raise McpProblem(400, f"The command must be one of {', '.join(sorted(STDIO_COMMANDS))}, or an absolute path to a program. Put arguments in args")
    if not isinstance(args, list) or not all(isinstance(a, str) and "\x00" not in a for a in args):
        raise McpProblem(400, "args must be a list of strings")


def _check_url(url: str, transport: str) -> None:
    parsed = urlparse(url or "")
    secure, plain = ("wss", "ws") if transport == "websocket" else ("https", "http")
    if parsed.scheme not in (secure, plain) or not parsed.hostname:
        raise McpProblem(400, f"A {transport} server needs a {secure}:// URL")
    if parsed.scheme == plain and parsed.hostname not in LOOPBACK:
        raise McpProblem(400, f"{secure}:// is required except for a loopback host")


def _secret_map(values: dict | None) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
        raise McpProblem(400, "env and headers must map names to string values")
    for value in values.values():
        register_secret(value)
    return values


def public(server: dict, tools: list[dict] | None = None) -> dict:
    """What any signed-in user may see: never a secret value, only the names."""
    keep = ("id", "name", "transport", "auth", "command", "url", "status", "error_message", "last_connected_at", "tools_listed_at", "owner", "plugin_id", "created_at", "updated_at")
    out = {k: server.get(k) for k in keep}
    out["args"] = json.loads(server.get("args") or "[]")
    out["secret_names"] = json.loads(server.get("secret_names") or "[]")
    if tools is not None:
        out["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": json.loads(t["parameters_schema"] or "{}")} for t in tools]
        out["tools_count"] = len(tools)
    return out


def get(server_id: str) -> dict:
    with db() as con:
        found = row(con.execute("SELECT * FROM mcp_servers WHERE id=?", (server_id,)))
    if not found:
        raise KeyError(f"MCP server {server_id}")
    return found


def secrets(server: dict) -> dict[str, str]:
    values = json.loads(decrypt(server["secrets_enc"].encode())) if server.get("secrets_enc") else {}
    for value in values.values():
        register_secret(value)
    return values


def tools(server_id: str) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT * FROM mcp_tools WHERE server_id=? ORDER BY name", (server_id,)))


def all_servers() -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT * FROM mcp_servers ORDER BY created_at, id"))


def _validated(body: dict) -> dict:
    transport = body.get("transport") or ("stdio" if body.get("command") else "http")
    if transport not in TRANSPORTS:
        raise McpProblem(400, f"transport is one of {', '.join(TRANSPORTS)}")
    name = str(body.get("name") or "").strip()
    if not name:
        raise McpProblem(400, "A server needs a name")
    args = body.get("args") or []
    if transport == "stdio":
        require_stdio_allowed()
        _check_command(str(body.get("command") or ""), args)
        found = {"command": body["command"], "args": args, "url": None, "secrets": _secret_map(body.get("env"))}
    else:
        _check_url(str(body.get("url") or ""), transport)
        found = {"command": None, "args": [], "url": body["url"], "secrets": _secret_map(body.get("headers"))}
    auth = body.get("auth") or "none"  # "oauth": each member signs in with OAuth 2.1 (core/mcp/oauth.py, R4)
    if auth not in ("none", "oauth") or (auth == "oauth" and transport != "http"):
        raise McpProblem(400, "auth is none, or oauth for an http server")
    return {"name": name, "transport": transport, "auth": auth, **found}


def _sealed(values: dict) -> tuple[str, str]:
    return (encrypt(json.dumps(values)).decode() if values else ""), json.dumps(sorted(values))


def add(body: dict, owner: str, plugin_id: str | None = None) -> dict:
    v = _validated(body)
    server_id, stamp = new_id("mcp"), now()
    enc, names = _sealed(v["secrets"])
    with db() as con:
        con.execute("INSERT INTO mcp_servers (id, name, type, transport, auth, command, args, url, status, error_message, secrets_enc, secret_names, owner, plugin_id, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,'',?,?,?,?,?,?)",
                    (server_id, v["name"], v["transport"], v["transport"], v["auth"], v["command"], json.dumps(v["args"]), v["url"], NOT_CONNECTED, enc, names, owner, plugin_id, stamp, stamp))
    return get(server_id)


def edit(server_id: str, body: dict) -> dict:
    """A changed server is a different server: its listed tools go and it must connect again. Grants stay."""
    old = get(server_id)
    merged = {"name": old["name"], "transport": old["transport"], "auth": old.get("auth") or "none", "command": old["command"], "args": json.loads(old["args"]), "url": old["url"], **{k: v for k, v in body.items() if v is not None}}
    secret_key = "env" if merged["transport"] == "stdio" else "headers"
    if merged.get(secret_key) is None:
        merged[secret_key] = secrets(old)
    v = _validated(merged)
    enc, names = _sealed(v["secrets"])
    with db() as con:
        con.execute("DELETE FROM mcp_tools WHERE server_id=?", (server_id,))
        con.execute("UPDATE mcp_servers SET name=?, type=?, transport=?, auth=?, oauth_client='', command=?, args=?, url=?, secrets_enc=?, secret_names=?, status=?, error_message='', tools_listed_at=NULL, updated_at=? WHERE id=?",
                    (v["name"], v["transport"], v["transport"], v["auth"], v["command"], json.dumps(v["args"]), v["url"], enc, names, NOT_CONNECTED, now(), server_id))
    return get(server_id)


def delete(server_id: str) -> None:
    get(server_id)
    with db() as con:
        con.execute("DELETE FROM mcp_servers WHERE id=?", (server_id,))  # tools and grants cascade


def mark_error(server_id: str, message: str) -> None:
    with db() as con:
        con.execute("DELETE FROM mcp_tools WHERE server_id=?", (server_id,))
        con.execute("UPDATE mcp_servers SET status=?, error_message=?, updated_at=? WHERE id=?", (ERROR, redact(message)[:2000] or "Connection failed", now(), server_id))


def store_tools(server_id: str, listed: list[dict]) -> None:
    """Replace the server's tools with exactly what list_tools returned, and mark it connected."""
    stamp = now()
    with db() as con:
        con.execute("DELETE FROM mcp_tools WHERE server_id=?", (server_id,))
        for t in listed:
            con.execute("INSERT INTO mcp_tools (id, server_id, name, description, parameters_schema, authorized, created_at, updated_at) VALUES (?,?,?,?,?,1,?,?)",
                        (new_id("tool"), server_id, t["name"], t["description"], json.dumps(t["input_schema"]), stamp, stamp))
        con.execute("UPDATE mcp_servers SET status=?, error_message='', last_connected_at=?, tools_listed_at=?, updated_at=? WHERE id=?", (CONNECTED, stamp, stamp, stamp, server_id))


def resolve_command(command: str) -> str:
    """The program's real path, found on PATH the way the OS finds it (npx is npx.cmd on Windows)."""
    found = command if Path(command).is_absolute() else shutil.which(command)
    if not found:
        raise McpProblem(400, f"Command not found on PATH: {command}")
    return found
