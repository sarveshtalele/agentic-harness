"""A real MCP server over stdio for the MCP tests: two tools, `echo` and `add`. Run: python mcp_echo_server.py"""
from mcp.server.mcpserver import MCPServer

server = MCPServer("echo-fixture")


@server.tool()
def echo(text: str) -> str:
    """Return the text unchanged."""
    return text


@server.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


if __name__ == "__main__":
    server.run("stdio")
