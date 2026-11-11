"""Who sees which capability, decided when the registry is read. The table holds everything; an admin sees all of it.

Anyone else sees only what they may use now: an enabled capability (a plugin's state and an agent's kill switch are read
live, not from the last sync), a plugin granted to their role (core/plugin_grants.py), an MCP tool their role was granted
on a connected server (core/mcp/grants.py), and only what runs under this profile (stdio MCP runs on local and desktop).
"""
from __future__ import annotations

from collections.abc import Callable

from backend import config
from backend.core import plugin_grants, plugins
from backend.core.mcp import grants
from backend.db import db

MCP_KINDS = ("mcp_server", "mcp_tool")


def is_admin(user: dict | None) -> bool:
    return bool(user) and user.get("role") == "admin"


def live(items: list[dict]) -> list[dict]:
    """Overlay the current enabled state of plugins and governed agents on the synced rows."""
    enabled = {p.id: p.enabled for p in plugins.discover()}
    with db() as con:
        agents_off = {r[0] for r in con.execute("SELECT agent FROM agent_settings WHERE enabled=0")}
    for item in items:
        if item["plugin"] and item["kind"] not in MCP_KINDS:
            item["enabled"] = enabled.get(item["plugin"], False)
        elif item["kind"] == "agent":
            item["enabled"] = item["name"] not in agents_off
    return items


def checker(user: dict | None) -> Callable[[dict], bool]:
    """`row -> bool` for this user over rows that went through `live`, reading the grants once."""
    if user is None or is_admin(user):
        return lambda _item: True
    granted = plugin_grants.allowed(plugin_grants.role_of(user))
    servers: dict[str, set] = {}

    def mcp_names(server_id: str) -> set:
        if server_id not in servers:
            servers[server_id] = set(grants.granted_names(server_id, user))
        return servers[server_id]

    def visible(item: dict) -> bool:
        if not item["enabled"] or config.PROFILE not in item["profiles"].split(","):
            return False
        if item["plugin"] and not granted(item["plugin"]):
            return False
        if item["kind"] in MCP_KINDS:
            names = mcp_names(item["meta"].get("server_id") or "")
            return bool(names) if item["kind"] == "mcp_server" else item["name"] in names
        return True
    return visible
