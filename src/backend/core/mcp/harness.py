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
            found.append(build(server, allowed=names))
        except registry.McpProblem:
            continue  # e.g. the command left PATH since it connected; the server page shows it on the next connect
    return found
