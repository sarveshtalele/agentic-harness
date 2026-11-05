-- Pre-seed Playwright MCP server if not already present
INSERT OR IGNORE INTO mcp_servers (id, name, type, transport, command, url, status, error_message, created_at, updated_at)
VALUES ('srv_playwright', 'Playwright Browser Automation', 'local_npx', 'stdio', 'npx -y @playwright/mcp@latest', NULL, 'connected', '', datetime('now'), datetime('now'));
