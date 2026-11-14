"""Add a requirement document to a project's index: parse, keep a versioned copy, save the text on disk, chunk, embed, index.

The parsed text is saved at `docs/sources/<doc-id>.md` in the project's workspace (through safe_path), so a quote can be checked
verbatim against the file later. Upload content is untrusted data: it is parsed and indexed, never run or followed.
"""
from __future__ import annotations

from backend.config import sandbox_dir
from backend.core import auth, documents, ledger
from backend.core.security import safe_path
from backend.core.source_text import UnsupportedFile, extract_text
from backend.rag import embed, store
from backend.rag.chunk import chunk_text

SUFFIXES = (".md", ".txt", ".docx", ".pdf")
SOURCES = "docs/sources"


def add(project_id: str, filename: str, blob: bytes, *, author: str | None = None, transport=None) -> dict:
    """Index one upload. Raises UnsupportedFile for a type or content that cannot be read."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not name.lower().endswith(SUFFIXES):
        raise UnsupportedFile(f"{name or 'The file'} is not a supported type. Upload {', '.join(SUFFIXES)}.")
    try:
        text = extract_text(name, blob)
    except UnsupportedFile:
        raise
    except Exception as exc:  # a corrupt .docx or .pdf: a clear refusal, not a 500
        raise UnsupportedFile(f"{name} could not be read as {name.rsplit('.', 1)[-1]}: {str(exc)[:160] or type(exc).__name__}") from exc
    if not text.strip():
        raise UnsupportedFile(f"{name} has no text to index (a scanned PDF needs OCR first).")
    who = author or auth.signer()
    doc = documents.create(project_id, "source", name, text, who, note=f"Uploaded {name}")  # redacted, versioned, hashed
    saved = doc["content"]  # what was stored, after redaction: the file, the chunks and the citations all use this text
    relative = f"{SOURCES}/{doc['id']}.md"
    target = safe_path(sandbox_dir(project_id), relative, for_write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(saved, encoding="utf-8")
    chunks = chunk_text(saved)
    vectors, note = embed.embed([c.text for c in chunks], transport=transport) if chunks else (None, "")
    embedded, note = store.save(project_id, doc["id"], name, doc["version"], doc["sha256"], relative, chunks, vectors, note)
    ledger.append(project_id, who, "rag.indexed", doc["id"], {"filename": name, "version": doc["version"], "sha256": doc["sha256"], "chunks": len(chunks), "embedded": embedded})
    return {"doc_id": doc["id"], "filename": name, "version": doc["version"], "chunks": len(chunks), "embedded": embedded, "source_path": relative, "note": note}
