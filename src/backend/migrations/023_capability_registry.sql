-- Capability registry (plan Phase R): every tool, agent, skill, command, workflow, stage, gate, plugin, hook, script and
-- MCP server or tool, derived from code and manifests by core/registry/sync.py. A sync replaces both tables at once.
CREATE TABLE IF NOT EXISTS capabilities (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  qualified_name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  when_to_use TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  plugin TEXT,
  sha256 TEXT NOT NULL,
  risk TEXT NOT NULL DEFAULT '',
  needs_approval INTEGER NOT NULL DEFAULT 0,
  profiles TEXT NOT NULL DEFAULT 'web,local,desktop',
  enabled INTEGER NOT NULL DEFAULT 1,
  meta TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_capabilities_kind ON capabilities(kind);
CREATE INDEX IF NOT EXISTS idx_capabilities_qualified ON capabilities(qualified_name);

CREATE TABLE IF NOT EXISTS capability_links (
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (from_id, to_id, relation, detail)
);
CREATE INDEX IF NOT EXISTS idx_capability_links_to ON capability_links(to_id);

-- One row per sync: the hash of every capability and link, so the harness cache knows when to refresh.
CREATE TABLE IF NOT EXISTS registry_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hash TEXT NOT NULL,
  capabilities INTEGER NOT NULL,
  links INTEGER NOT NULL,
  problems TEXT NOT NULL DEFAULT '[]',
  synced_by TEXT NOT NULL,
  synced_at TEXT NOT NULL
);
