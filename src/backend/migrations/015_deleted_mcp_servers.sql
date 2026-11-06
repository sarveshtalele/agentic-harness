-- Track deleted MCP servers so pre-seed / sync routines do not resurrect them
CREATE TABLE IF NOT EXISTS deleted_mcp_servers (
  id TEXT PRIMARY KEY,
  deleted_at TEXT NOT NULL
);
