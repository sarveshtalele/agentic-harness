from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class MCPServerConfig(BaseModel):
    id: str
    name: str
    transport: str = "stdio"  # stdio or sse
    command: Optional[str] = None
    args: Optional[List[str]] = None
    sseUrl: Optional[str] = None
    status: str = "connected"
    toolsCount: int = 0

class MCPClientManager:
    """
    MAF Model Context Protocol (MCP) Client Manager (agent-framework.pdf pp. 410-448)
    Manages stdio & SSE MCP server configurations and real-time remote tools.
    """
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self._init_default_servers()

    def _init_default_servers(self):
        defaults = [
            MCPServerConfig(
                id="mcp-playwright",
                name="Playwright Browser MCP",
                transport="stdio",
                command="npx",
                args=["@executeautomation/playwright-mcp-server"],
                status="connected",
                toolsCount=4
            ),
            MCPServerConfig(
                id="mcp-github",
                name="GitHub Repository MCP",
                transport="stdio",
                command="npx",
                args=["@modelcontextprotocol/server-github"],
                status="connected",
                toolsCount=6
            ),
            MCPServerConfig(
                id="mcp-postgres",
                name="PostgreSQL Database MCP",
                transport="stdio",
                command="npx",
                args=["@modelcontextprotocol/server-postgres"],
                status="disconnected",
                toolsCount=3
            ),
        ]
        for s in defaults:
            self.servers[s.id] = s

    def list_servers(self) -> List[Dict[str, Any]]:
        return [s.model_dump() for s in self.servers.values()]

    def add_server(self, config: MCPServerConfig) -> MCPServerConfig:
        self.servers[config.id] = config
        return config

    def remove_server(self, server_id: str) -> bool:
        if server_id in self.servers:
            del self.servers[server_id]
            return True
        return False
