-- Real MCP: servers keep an argument list, encrypted secrets, timestamps, owner, and plugin. Tools come only from a real list_tools.
ALTER TABLE mcp_servers ADD COLUMN args TEXT NOT NULL DEFAULT '[]';
ALTER TABLE mcp_servers ADD COLUMN secrets_enc TEXT NOT NULL DEFAULT '';
ALTER TABLE mcp_servers ADD COLUMN secret_names TEXT NOT NULL DEFAULT '[]';
ALTER TABLE mcp_servers ADD COLUMN last_connected_at TEXT;
ALTER TABLE mcp_servers ADD COLUMN tools_listed_at TEXT;
ALTER TABLE mcp_servers ADD COLUMN owner TEXT NOT NULL DEFAULT '';
ALTER TABLE mcp_servers ADD COLUMN plugin_id TEXT;

-- The five servers earlier code seeded, with hardcoded tool lists. 014 stored srv_playwright as 'connected' although no
-- code could open a session before this migration, so tools_listed_at IS NULL (never listed) marks that status as untrue.
DELETE FROM mcp_tools WHERE server_id IN (SELECT id FROM mcp_servers
  WHERE id IN ('mcp-filesystem', 'mcp-memory', 'mcp-fetch', 'mcp-github', 'srv_playwright') AND (status != 'connected' OR tools_listed_at IS NULL));
DELETE FROM mcp_servers WHERE id IN ('mcp-filesystem', 'mcp-memory', 'mcp-fetch', 'mcp-github', 'srv_playwright') AND (status != 'connected' OR tools_listed_at IS NULL);
-- No row before this migration came from a real list_tools: earlier code never opened an MCP session.
DELETE FROM mcp_tools WHERE server_id IN (SELECT id FROM mcp_servers WHERE tools_listed_at IS NULL);
UPDATE mcp_servers SET status = 'not_connected' WHERE tools_listed_at IS NULL;

CREATE TABLE IF NOT EXISTS mcp_grants (
  id TEXT PRIMARY KEY,
  server_id TEXT NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
  tool_name TEXT NOT NULL,
  role TEXT NOT NULL,
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  UNIQUE (server_id, tool_name, role)
);

CREATE TABLE IF NOT EXISTS plugin_state (
  plugin_id TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL,
  updated_by TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
