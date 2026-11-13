"""MCP tools for the project harness: connected servers only, each filtered to the tools the user's role was granted."""
from __future__ import annotations

from backend.core.auth import can_see_project
from backend.core.mcp import grants, registry
from backend.core.mcp.connect import build


def mcp_tools_for(project_id: str, user: dict) -> list:
    """Unconnected MAF MCP tools (MCPStdioTool / MCPStreamableHTTPTool / MCPWebsocketTool), one per connected server
    with at least one granted tool, `allowed_tools` set to exactly the granted names. The agent opens and closes the
    sessions when it runs. A user who cannot see the project gets none. Under the `web` profile stdio servers are left out.
    """
    if not can_see_project(project_id, user):
        return []
    found = []
    for server in registry.all_servers():
        if server["status"] != registry.CONNECTED or (server["transport"] == "stdio" and not registry.stdio_allowed()):
            continue
        names = grants.granted_names(server["id"], user)
        if not names:
            continue
        try:
            found.append(build(server, allowed=names, user_id=user["id"]))  # an OAuth server needs this member signed in (R4)
        except registry.McpProblem:
            continue  # e.g. the command left PATH since it connected; the server page shows it on the next connect
    return found


STALE_MINUTES = 10
_refreshing: set[str] = set()


def refresh_stale(minutes: int = STALE_MINUTES) -> list[str]:
    """Re-list the tools of connected servers whose stored list is older than `minutes`, in a background thread, so a
    tool added or removed on a server reaches the catalogue from the next turn (docs/PHASE2_PLAN.md section 8). A server
    that fails is marked with its error by `connect`, as on the MCP page. Returns the ids being refreshed."""
    import asyncio
    import threading
    from datetime import datetime, timedelta

    from backend.core.mcp.connect import connect

    cutoff = datetime.now().astimezone() - timedelta(minutes=minutes)
    due = []
    for server in registry.all_servers():
        if server["status"] != registry.CONNECTED or server["id"] in _refreshing or (server["transport"] == "stdio" and not registry.stdio_allowed()):
            continue
        if server.get("auth") == "oauth":
            continue  # its tools are listed with a member's own sign-in; the admin's Connect refreshes them
        try:
            listed = datetime.fromisoformat(server.get("tools_listed_at") or "")
        except ValueError:
            listed = None
        if listed is None or (listed.tzinfo and listed < cutoff) or (not listed.tzinfo and listed < cutoff.replace(tzinfo=None)):
            due.append(server["id"])
    if not due:
        return []
    _refreshing.update(due)

    def work():
        for server_id in due:
            try:
                asyncio.run(connect(server_id))
            except Exception:  # noqa: BLE001 - connect stores its own error; a refresh never breaks a turn
                pass
            finally:
                _refreshing.discard(server_id)

    threading.Thread(target=work, daemon=True).start()
    return due
