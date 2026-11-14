-- QE v2 step 4 (docs/QE_V2_PLAN.md section 5): requirement documents split into chunks for retrieval.
-- Keyword search is a generated tsvector. Vectors live in rag_vectors, which backend/rag/store.py creates only when the
-- pgvector extension can be installed; without it search is keyword only and the API says so.
CREATE TABLE rag_sources (
  doc_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  version BIGINT NOT NULL,
  sha256 TEXT NOT NULL,
  chunk_count BIGINT NOT NULL,
  embedded BIGINT NOT NULL DEFAULT 0,
  embed_note TEXT NOT NULL DEFAULT '',
  source_path TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE rag_chunks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  doc_id TEXT NOT NULL REFERENCES rag_sources(doc_id) ON DELETE CASCADE,
  version BIGINT NOT NULL,
  ord BIGINT NOT NULL,
  section TEXT NOT NULL DEFAULT '',
  page BIGINT,
  line_start BIGINT NOT NULL,
  line_end BIGINT NOT NULL,
  body TEXT NOT NULL,
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', body || ' ' || section)) STORED
);
CREATE INDEX rag_chunks_project ON rag_chunks (project_id, doc_id, ord);
CREATE INDEX rag_chunks_tsv ON rag_chunks USING GIN (tsv);
