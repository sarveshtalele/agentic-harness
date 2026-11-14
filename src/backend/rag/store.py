"""PostgreSQL side of the document index: chunks with a tsvector, and pgvector embeddings when the extension exists."""
from __future__ import annotations

from backend.db import db, new_id, now, rows
from backend.rag.chunk import Chunk


def vector_available(con) -> str:
    """"" when the pgvector extension is installed in this database (creating it when the server has it), else why not."""
    try:
        con.raw.execute("SAVEPOINT vec")
        con.raw.execute("CREATE EXTENSION IF NOT EXISTS vector")
        con.raw.execute("RELEASE SAVEPOINT vec")
        return ""
    except Exception as exc:  # noqa: BLE001 - the reason is shown to the user
        con.raw.execute("ROLLBACK TO SAVEPOINT vec")
        return f"pgvector is not installed in this PostgreSQL ({str(exc).strip().splitlines()[0][:140]}), so search is keyword only."


def save(project_id: str, doc_id: str, filename: str, version: int, digest: str, source_path: str, chunks: list[Chunk],
         vectors: list[list[float]] | None, note: str) -> tuple[int, str]:
    """Replace the document's chunks. Vectors go in only when pgvector is there; returns how many chunks have one and the note to show."""
    ids = [new_id("chk") for _ in chunks]
    embedded = 0
    with db() as con:
        con.execute("DELETE FROM rag_sources WHERE doc_id=?", (doc_id,))
        con.execute("INSERT INTO rag_sources (doc_id, project_id, filename, version, sha256, chunk_count, embedded, embed_note, source_path, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (doc_id, project_id, filename, version, digest, len(chunks), 0, "", source_path, now()))
        con.executemany("INSERT INTO rag_chunks (id, project_id, doc_id, version, ord, section, page, line_start, line_end, body) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [(i, project_id, doc_id, version, c.ord, c.section, c.page, c.line_start, c.line_end, c.text) for i, c in zip(ids, chunks)])
        if vectors:
            problem = vector_available(con)
            if problem:
                note = f"{note} {problem}".strip()
            else:
                con.raw.execute("CREATE TABLE IF NOT EXISTS rag_vectors (chunk_id TEXT PRIMARY KEY REFERENCES rag_chunks(id) ON DELETE CASCADE, embedding vector NOT NULL)")
                for i, v in zip(ids, vectors):
                    con.raw.execute("INSERT INTO rag_vectors (chunk_id, embedding) VALUES (%s, %s::vector)", (i, "[" + ",".join(map(str, v)) + "]"))
                embedded = len(vectors)
        con.execute("UPDATE rag_sources SET embedded=?, embed_note=? WHERE doc_id=?", (embedded, note, doc_id))
    return embedded, note


def sources(project_id: str) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT doc_id, filename, version, sha256, chunk_count, embedded, embed_note, source_path, created_at FROM rag_sources WHERE project_id=? ORDER BY created_at, doc_id", (project_id,)))


def keyword(project_id: str, tsquery: str, limit: int) -> list[dict]:
    with db() as con:
        cur = con.raw.execute(
            "SELECT c.id, c.doc_id, c.version, c.section, c.page, c.line_start, c.line_end, c.body, s.filename, s.source_path FROM rag_chunks c "
            "JOIN rag_sources s ON s.doc_id=c.doc_id WHERE c.project_id=%s AND c.tsv @@ to_tsquery('english', %s) "
            "ORDER BY ts_rank_cd(c.tsv, to_tsquery('english', %s)) DESC, c.doc_id, c.ord LIMIT %s", (project_id, tsquery, tsquery, limit))
        return [dict(zip(r.keys(), r)) for r in cur.fetchall()]


def nearest(project_id: str, vector: list[float], limit: int) -> list[dict]:
    """Chunks by cosine distance, [] when there is no vector table or none of this size."""
    with db() as con:
        if not con.raw.execute("SELECT to_regclass('rag_vectors')").fetchone()[0]:
            return []
        literal = "[" + ",".join(map(str, vector)) + "]"
        cur = con.raw.execute(
            "SELECT c.id, c.doc_id, c.version, c.section, c.page, c.line_start, c.line_end, c.body, s.filename, s.source_path FROM rag_vectors v "
            "JOIN rag_chunks c ON c.id=v.chunk_id JOIN rag_sources s ON s.doc_id=c.doc_id WHERE c.project_id=%s AND vector_dims(v.embedding)=%s "
            "ORDER BY v.embedding <=> %s::vector LIMIT %s", (project_id, len(vector), literal, limit))
        return [dict(zip(r.keys(), r)) for r in cur.fetchall()]
