-- PostgreSQL baseline: the final schema of SQLite migrations 001 to 023, converted (MASTER_PLAN Part 3, G5).
-- INTEGER is BIGINT, REAL is DOUBLE PRECISION, BLOB is BYTEA, AUTOINCREMENT is an identity column. Tables that
-- queries order by insertion keep that order through an explicit `rowid` identity column, placed last. Text keeps ISO timestamps.

CREATE TABLE projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, archived BIGINT NOT NULL DEFAULT 0
, owner_id TEXT);

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE credentials (
  id TEXT PRIMARY KEY, provider TEXT NOT NULL, label TEXT NOT NULL, login TEXT NOT NULL DEFAULT '',
  secret BYTEA NOT NULL, scopes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);

CREATE TABLE repo_sources (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, url TEXT NOT NULL DEFAULT '', ref TEXT NOT NULL DEFAULT '',
  credential_id TEXT, commit_sha TEXT NOT NULL DEFAULT '', analysis TEXT NOT NULL DEFAULT '{}',
  scanned_at TEXT NOT NULL
);

CREATE TABLE sources (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, sha256 TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(project_id, sha256)
);

CREATE TABLE templates (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, builtin BIGINT NOT NULL DEFAULT 0,
  sha256 TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE documents (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
  current_version BIGINT NOT NULL DEFAULT 0, parent_id TEXT, template_id TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE TABLE document_versions (
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, version BIGINT NOT NULL,
  content TEXT NOT NULL, data TEXT NOT NULL DEFAULT 'null', sha256 TEXT NOT NULL, author TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '', prompt_ref TEXT NOT NULL DEFAULT '', run_id TEXT, created_at TEXT NOT NULL,
  PRIMARY KEY (document_id, version)
);

CREATE TABLE prompts (
  agent TEXT NOT NULL, version BIGINT NOT NULL, body TEXT NOT NULL, sha256 TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '', author TEXT NOT NULL, active BIGINT NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
  PRIMARY KEY (agent, version)
);

CREATE TABLE runs (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  workflow TEXT NOT NULL, status TEXT NOT NULL, input TEXT NOT NULL, state TEXT NOT NULL DEFAULT '{}',
  error TEXT NOT NULL DEFAULT '', tokens_in BIGINT NOT NULL DEFAULT 0, tokens_out BIGINT NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL, ended_at TEXT
, user_id TEXT, model TEXT NOT NULL DEFAULT '');

CREATE TABLE run_events (
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, seq BIGINT NOT NULL,
  type TEXT NOT NULL, stage TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '',
  data TEXT NOT NULL DEFAULT '{}', ts TEXT NOT NULL, PRIMARY KEY (run_id, seq),
  rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE -- last, so positional inserts without it still work
);

CREATE TABLE approvals (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, gate BIGINT, title TEXT NOT NULL,
  summary TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'pending',
  decided_by TEXT, feedback TEXT, created_at TEXT NOT NULL, decided_at TEXT
);

CREATE TABLE gates (
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, gate BIGINT NOT NULL,
  status TEXT NOT NULL, decided_by TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', run_id TEXT,
  signature TEXT NOT NULL, decided_at TEXT NOT NULL, PRIMARY KEY (project_id, gate)
);

CREATE TABLE ledger (
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, seq BIGINT NOT NULL, ts TEXT NOT NULL,
  actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL DEFAULT '', data TEXT NOT NULL DEFAULT '{}',
  prev_hash TEXT NOT NULL, hash TEXT NOT NULL, PRIMARY KEY (project_id, seq),
  rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE -- last, so positional inserts without it still work
);

CREATE TABLE findings (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, run_id TEXT,
  source TEXT NOT NULL, rule TEXT NOT NULL, severity TEXT NOT NULL, title TEXT NOT NULL, file TEXT NOT NULL,
  line BIGINT NOT NULL, evidence TEXT NOT NULL, explanation TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open', fingerprint TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(project_id, fingerprint)
);

CREATE TABLE chat_threads (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL, agent TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
, model TEXT NOT NULL DEFAULT '');

CREATE TABLE chat_messages (
  thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE, seq BIGINT NOT NULL, id TEXT NOT NULL,
  role TEXT NOT NULL, content TEXT NOT NULL, agent TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
  PRIMARY KEY (thread_id, seq)
);

CREATE TABLE memories (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  content TEXT NOT NULL, source TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);

CREATE TABLE evaluations (
  id TEXT PRIMARY KEY, agent TEXT NOT NULL, prompt_ref TEXT NOT NULL, passed BIGINT NOT NULL,
  total BIGINT NOT NULL, results TEXT NOT NULL, created_at TEXT NOT NULL,
  rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE -- last, so positional inserts without it still work
);

CREATE TABLE agent_settings (
  agent TEXT PRIMARY KEY, enabled BIGINT NOT NULL DEFAULT 1, max_tokens BIGINT,
  updated_by TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
, model TEXT NOT NULL DEFAULT '');

CREATE TABLE guardrail_events (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, agent TEXT NOT NULL, project_id TEXT, run_id TEXT,
  kind TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE agent_calls (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, agent TEXT NOT NULL, project_id TEXT, run_id TEXT, source TEXT NOT NULL,
  prompt_ref TEXT NOT NULL, tokens_in BIGINT NOT NULL DEFAULT 0, tokens_out BIGINT NOT NULL DEFAULT 0,
  latency_ms BIGINT NOT NULL DEFAULT 0, tool_calls BIGINT NOT NULL DEFAULT 0, status TEXT NOT NULL,
  error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
, model TEXT NOT NULL DEFAULT '', user_id TEXT, skills TEXT NOT NULL DEFAULT '');

CREATE TABLE tool_calls (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, agent TEXT NOT NULL, project_id TEXT, run_id TEXT, source TEXT NOT NULL,
  tool TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'function', arguments TEXT NOT NULL DEFAULT '{}',
  latency_ms BIGINT NOT NULL DEFAULT 0, status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
, trace_id TEXT, span_id TEXT);

CREATE TABLE users (
  id TEXT PRIMARY KEY, username_lookup TEXT NOT NULL UNIQUE, username_enc TEXT NOT NULL, password_hash TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT '', token_limit BIGINT, active_from TEXT, active_until TEXT,
  enabled BIGINT NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
, role TEXT NOT NULL DEFAULT 'developer' CHECK (role IN ('qe_lead','ba','developer','viewer')), email_enc TEXT NOT NULL DEFAULT '');

CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL
, last_seen TEXT);

CREATE TABLE auth_events (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, subject TEXT NOT NULL, event TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE run_failures (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  code TEXT NOT NULL, message TEXT NOT NULL, action TEXT NOT NULL, retryable BIGINT NOT NULL DEFAULT 0,
  stage TEXT NOT NULL DEFAULT '', agent TEXT NOT NULL DEFAULT '', attempt BIGINT, prompt_ref TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
  finish_reason TEXT NOT NULL DEFAULT '', tokens_in BIGINT, tokens_out BIGINT, duration_ms BIGINT,
  parse_pos BIGINT, parse_context TEXT NOT NULL DEFAULT '', technical TEXT NOT NULL DEFAULT '', reply_file TEXT NOT NULL DEFAULT '',
  stack TEXT NOT NULL DEFAULT '', provider_status BIGINT, provider_request_id TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
  rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE -- last, so positional inserts without it still work
);

CREATE TABLE models (
  name TEXT PRIMARY KEY, label TEXT NOT NULL DEFAULT '', enabled BIGINT NOT NULL DEFAULT 1,
  is_default BIGINT NOT NULL DEFAULT 0, created_at TEXT NOT NULL
, tools_status TEXT NOT NULL DEFAULT '', tools_reason TEXT NOT NULL DEFAULT '', tools_checked_at TEXT, tools_max_tokens BIGINT);

CREATE TABLE user_models (
  user_id TEXT NOT NULL, model TEXT NOT NULL, PRIMARY KEY (user_id, model)
);

CREATE TABLE user_limits (
  user_id TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', period TEXT NOT NULL CHECK (period IN ('day','week','month')),
  tokens BIGINT NOT NULL CHECK (tokens >= 0), PRIMARY KEY (user_id, model, period)
);

CREATE TABLE project_members (
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, user_id TEXT NOT NULL REFERENCES users(id),
  role TEXT NOT NULL CHECK (role IN ('qe_lead','ba','developer','viewer')), added_by TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (project_id, user_id)
);

CREATE TABLE evaluation_metrics (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, eval_id TEXT NOT NULL DEFAULT '', batch TEXT NOT NULL DEFAULT '', agent TEXT NOT NULL, prompt_ref TEXT NOT NULL,
  metric TEXT NOT NULL, value DOUBLE PRECISION, status TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', n BIGINT NOT NULL DEFAULT 0,
  judge_model TEXT NOT NULL DEFAULT '', self_graded BIGINT NOT NULL DEFAULT 0, labels_reviewed BIGINT, tokens BIGINT NOT NULL DEFAULT 0,
  detail TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'eval', agent_call_id BIGINT, benchmark TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);

CREATE TABLE mcp_servers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'local_npx',
  transport TEXT NOT NULL DEFAULT 'stdio',
  command TEXT,
  url TEXT,
  status TEXT NOT NULL DEFAULT 'connected',
  error_message TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
, args TEXT NOT NULL DEFAULT '[]', secrets_enc TEXT NOT NULL DEFAULT '', secret_names TEXT NOT NULL DEFAULT '[]', last_connected_at TEXT, tools_listed_at TEXT, owner TEXT NOT NULL DEFAULT '', plugin_id TEXT);

CREATE TABLE mcp_tools (
  id TEXT PRIMARY KEY,
  server_id TEXT NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  parameters_schema TEXT NOT NULL DEFAULT '{}',
  authorized BIGINT NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE deleted_mcp_servers (
  id TEXT PRIMARY KEY,
  deleted_at TEXT NOT NULL
);

CREATE TABLE skill_plans (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, author TEXT NOT NULL, kind TEXT NOT NULL, request TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL, source_ref TEXT NOT NULL DEFAULT '', source_text TEXT NOT NULL, source_sha256 TEXT NOT NULL,
  revise TEXT NOT NULL DEFAULT '', plan_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft', plan_sha256 TEXT NOT NULL DEFAULT '',
  approved_by TEXT NOT NULL DEFAULT '', approved_at TEXT, prompt_ref TEXT NOT NULL DEFAULT '',
  draft_sha256 TEXT NOT NULL DEFAULT '', checks_json TEXT NOT NULL DEFAULT '', generated_at TEXT, created_at TEXT NOT NULL
);

CREATE TABLE skill_versions (
  name TEXT NOT NULL, version BIGINT NOT NULL, sha256 TEXT NOT NULL, files_json TEXT NOT NULL, author TEXT NOT NULL,
  plan_id TEXT, project_id TEXT NOT NULL DEFAULT '', prompt_ref TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
  PRIMARY KEY (name, version)
);

CREATE TABLE mcp_grants (
  id TEXT PRIMARY KEY,
  server_id TEXT NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
  tool_name TEXT NOT NULL,
  role TEXT NOT NULL,
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  UNIQUE (server_id, tool_name, role)
);

CREATE TABLE plugin_state (
  plugin_id TEXT PRIMARY KEY,
  enabled BIGINT NOT NULL,
  updated_by TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE harness_snapshots (
  scope TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  body TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (scope, thread_id)
);

CREATE TABLE plugin_grants (
  id TEXT PRIMARY KEY,
  plugin_id TEXT NOT NULL,
  role TEXT NOT NULL,
  granted_by TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  UNIQUE (plugin_id, role)
);

CREATE TABLE spans (
  span_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  parent_id TEXT,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL,
  duration_ms BIGINT NOT NULL,
  status TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}',
  project_id TEXT,
  user_id TEXT,
  root BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE sandbox_leases (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  user_id TEXT,
  kind TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  expires_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE capabilities (
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
  needs_approval BIGINT NOT NULL DEFAULT 0,
  profiles TEXT NOT NULL DEFAULT 'web,local,desktop',
  enabled BIGINT NOT NULL DEFAULT 1,
  meta TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE capability_links (
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (from_id, to_id, relation, detail)
);

CREATE TABLE registry_versions (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  hash TEXT NOT NULL,
  capabilities BIGINT NOT NULL,
  links BIGINT NOT NULL,
  problems TEXT NOT NULL DEFAULT '[]',
  synced_by TEXT NOT NULL,
  synced_at TEXT NOT NULL
);

CREATE INDEX idx_documents_project ON documents(project_id, kind);

CREATE INDEX idx_runs_project ON runs(project_id, started_at);

CREATE INDEX idx_threads_project ON chat_threads(project_id, updated_at);

CREATE INDEX idx_agent_calls_agent ON agent_calls(agent, created_at);

CREATE INDEX idx_guardrail_agent ON guardrail_events(agent, created_at);

CREATE INDEX idx_tool_calls_project ON tool_calls(project_id, created_at);

CREATE INDEX idx_tool_calls_run ON tool_calls(run_id);

CREATE INDEX idx_projects_owner ON projects(owner_id);

CREATE INDEX idx_run_failures_run ON run_failures(run_id, created_at);

CREATE INDEX idx_run_events_ts ON run_events(ts);

CREATE INDEX idx_agent_calls_ts ON agent_calls(created_at);

CREATE INDEX idx_agent_calls_project ON agent_calls(project_id, created_at);

CREATE INDEX idx_agent_calls_run ON agent_calls(run_id);

CREATE INDEX idx_tool_calls_ts ON tool_calls(created_at);

CREATE INDEX idx_guardrail_ts ON guardrail_events(created_at);

CREATE INDEX idx_guardrail_project ON guardrail_events(project_id, created_at);

CREATE INDEX idx_guardrail_run ON guardrail_events(run_id);

CREATE INDEX idx_ledger_ts ON ledger(ts);

CREATE INDEX idx_runs_active ON runs(project_id, workflow) WHERE status IN ('running','waiting_approval');

CREATE INDEX idx_agent_calls_user ON agent_calls(user_id, created_at);

CREATE INDEX idx_agent_calls_user_model ON agent_calls(user_id, model, created_at);

CREATE INDEX idx_members_user ON project_members(user_id);

CREATE INDEX idx_evalmetrics_agent ON evaluation_metrics(agent, prompt_ref, metric);

CREATE INDEX idx_evalmetrics_batch ON evaluation_metrics(batch);

CREATE INDEX idx_mcp_tools_server_id ON mcp_tools(server_id);

CREATE INDEX idx_skill_plans_project ON skill_plans(project_id, created_at);

CREATE INDEX idx_spans_trace ON spans(trace_id);

CREATE INDEX idx_spans_roots ON spans(root, started_at);

CREATE INDEX idx_spans_started ON spans(started_at);

CREATE INDEX idx_capabilities_kind ON capabilities(kind);

CREATE INDEX idx_capabilities_qualified ON capabilities(qualified_name);

CREATE INDEX idx_capability_links_to ON capability_links(to_id);

