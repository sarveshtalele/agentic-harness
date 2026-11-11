-- MAF AG-UI thread snapshots for the project harness: the latest replayable state of one chat thread per person
-- (scope is "<project>/<user>"). Plan or execute mode and pending tool approvals live in it across requests.
CREATE TABLE IF NOT EXISTS harness_snapshots (
  scope TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  body TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (scope, thread_id)
);
