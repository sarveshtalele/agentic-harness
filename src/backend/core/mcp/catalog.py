"""Install templates an admin may add as servers. Templates only: nothing here is registered or connected."""
from __future__ import annotations

TEMPLATES = [
    {"id": "playwright", "name": "Playwright browser", "transport": "stdio", "command": "npx", "args": ["-y", "@playwright/mcp@latest"],
     "env_names": [], "description": "Browser automation from Microsoft. Needs Node.js."},
    {"id": "filesystem", "name": "Filesystem", "transport": "stdio", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "<folder>"],
     "env_names": [], "description": "Read and write files under the folder you name. Replace <folder> with an absolute path."},
    {"id": "fetch", "name": "Fetch", "transport": "stdio", "command": "uvx", "args": ["mcp-server-fetch"],
     "env_names": [], "description": "Fetch a URL and return it as markdown. Needs uv."},
    {"id": "github", "name": "GitHub", "transport": "http", "url": "https://api.githubcopilot.com/mcp/",
     "header_names": ["Authorization"], "description": "GitHub's remote MCP server. Set the Authorization header to Bearer <token>."},
]
