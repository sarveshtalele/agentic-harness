-- Which roles may use a plugin's skills and commands (HS-12). A plugin with no rows is open to every role;
-- once it has a row, only the granted roles and the admin may use it.
CREATE TABLE IF NOT EXISTS plugin_grants (
  id TEXT PRIMARY KEY,
  plugin_id TEXT NOT NULL,
  role TEXT NOT NULL,
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  UNIQUE (plugin_id, role)
);
