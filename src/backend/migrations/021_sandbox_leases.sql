-- Harness sandbox slots on the web profile (plan H2): one row per running shell command or file write. A row past
-- expires_at (epoch seconds) belongs to a process that died, and the next acquire removes it.
CREATE TABLE IF NOT EXISTS sandbox_leases (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  user_id TEXT,
  kind TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  expires_at REAL NOT NULL
);
