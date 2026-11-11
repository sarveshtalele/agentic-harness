"""Which role may call which MCP tool. No grant means not callable: an admin grants each server or tool per role."""
from __future__ import annotations

from backend.core.auth import ROLES
from backend.db import db, new_id, now, row, rows

GRANT_ROLES = ("admin", *ROLES)
ALL = "*"


def _role(user: dict) -> str:
    return "admin" if user.get("role") == "admin" else str(user.get("account_role") or "")


def add(server_id: str, tool_name: str, role: str, by: str) -> dict:
    if role not in GRANT_ROLES:
        raise ValueError(f"role is one of: {', '.join(GRANT_ROLES)}")
    tool_name = (tool_name or "").strip()
    if not tool_name:
        raise ValueError("tool_name is a tool's name, or * for every tool the server lists")
    with db() as con:
        if not con.execute("SELECT 1 FROM mcp_servers WHERE id=?", (server_id,)).fetchone():
            raise KeyError(f"MCP server {server_id}")
        con.execute("INSERT OR IGNORE INTO mcp_grants (id, server_id, tool_name, role, granted_by, granted_at) VALUES (?,?,?,?,?,?)",
                    (new_id("grant"), server_id, tool_name, role, by, now()))
        return row(con.execute("SELECT * FROM mcp_grants WHERE server_id=? AND tool_name=? AND role=?", (server_id, tool_name, role)))


def remove(grant_id: str) -> None:
    with db() as con:
        if not con.execute("DELETE FROM mcp_grants WHERE id=?", (grant_id,)).rowcount:
            raise KeyError(f"grant {grant_id}")


def listing(server_id: str | None = None) -> list[dict]:
    with db() as con:
        if server_id:
            return rows(con.execute("SELECT * FROM mcp_grants WHERE server_id=? ORDER BY granted_at", (server_id,)))
        return rows(con.execute("SELECT * FROM mcp_grants ORDER BY granted_at"))


def granted_names(server_id: str, user: dict) -> list[str]:
    """The listed tools of a server this user's role may call."""
    with db() as con:
        names = [r[0] for r in con.execute("SELECT tool_name FROM mcp_grants WHERE server_id=? AND role=?", (server_id, _role(user)))]
        listed = [r[0] for r in con.execute("SELECT name FROM mcp_tools WHERE server_id=? ORDER BY name", (server_id,))]
    return listed if ALL in names else [n for n in listed if n in names]


def allows(server_id: str, tool_name: str, user: dict) -> bool:
    return tool_name in granted_names(server_id, user)
