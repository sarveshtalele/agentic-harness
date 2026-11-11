-- H9: finished OpenTelemetry spans for the trace explorer. Attributes are redacted before they are written.
-- A root span (no parent) is one run: an API request, a chat turn, or a background workflow run.
CREATE TABLE IF NOT EXISTS spans (
  span_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  parent_id TEXT,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL,
  duration_ms INTEGER NOT NULL,
  status TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}',
  project_id TEXT,
  user_id TEXT,
  root INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_roots ON spans(root, started_at);
CREATE INDEX IF NOT EXISTS idx_spans_started ON spans(started_at);
-- The span that wrapped each tool call, so a tool_calls row and its span share one id.
ALTER TABLE tool_calls ADD COLUMN trace_id TEXT;
ALTER TABLE tool_calls ADD COLUMN span_id TEXT;
