-- Skill Studio (plan M3). A plan is a draft until a named person approves it; approval stores plan_sha256 over the
-- canonical plan JSON, and generation refuses a plan whose stored JSON no longer hashes to it.
-- status: draft, approved, generated. source_text is untrusted data, redacted before it is stored.
CREATE TABLE skill_plans (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, author TEXT NOT NULL, kind TEXT NOT NULL, request TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL, source_ref TEXT NOT NULL DEFAULT '', source_text TEXT NOT NULL, source_sha256 TEXT NOT NULL,
  revise TEXT NOT NULL DEFAULT '', plan_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft', plan_sha256 TEXT NOT NULL DEFAULT '',
  approved_by TEXT NOT NULL DEFAULT '', approved_at TEXT, prompt_ref TEXT NOT NULL DEFAULT '',
  draft_sha256 TEXT NOT NULL DEFAULT '', checks_json TEXT NOT NULL DEFAULT '', generated_at TEXT, created_at TEXT NOT NULL
);
CREATE INDEX idx_skill_plans_project ON skill_plans(project_id, created_at);
-- One immutable row per published version. A deleted skill keeps every row. plan_id is NULL for a zip upload.
CREATE TABLE skill_versions (
  name TEXT NOT NULL, version INTEGER NOT NULL, sha256 TEXT NOT NULL, files_json TEXT NOT NULL, author TEXT NOT NULL,
  plan_id TEXT, project_id TEXT NOT NULL DEFAULT '', prompt_ref TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
  PRIMARY KEY (name, version)
);
