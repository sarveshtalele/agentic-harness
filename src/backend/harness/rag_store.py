"""
ChromaDB RAG Vector Store & Multi-DB Grounding Engine
Indexes project documents, BRDs, test specifications, and code into ChromaDB.
Provides semantic search and multi-database grounding across SQLite, ChromaDB, and AST discoveries.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class RAGVectorStore:
    """Manages ChromaDB collections partitioned by project with persistent disk storage."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or os.path.join(os.getcwd(), "data", "chromadb")
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = None
        self._init_client()

    def _init_client(self):
        if not HAS_CHROMADB:
            return
        try:
            self.client = chromadb.PersistentClient(path=self.persist_dir)
        except Exception as exc:
            print(f"[RAG Vector Store] PersistentClient error: {exc}. Using ephemeral client.")
            try:
                self.client = chromadb.Client()
            except Exception:
                self.client = None

    def get_collection(self, project_id: str):
        if not self.client:
            return None
        safe_name = f"proj_{re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)}"[:60]
        try:
            return self.client.get_or_create_collection(
                name=safe_name,
                metadata={"hnsw:space": "cosine", "project_id": project_id}
            )
        except Exception as exc:
            print(f"[RAG Vector Store] get_or_create_collection error: {exc}")
            return None

    def chunk_document(self, content: str, max_chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
        """Splits markdown or text document into semantic heading-aligned chunks."""
        if not content:
            return []

        # Split on markdown headings first
        sections = re.split(r'(?m)(?=^#{1,3}\s+)', content)
        chunks = []
        chunk_idx = 0

        for sec in sections:
            sec_text = sec.strip()
            if not sec_text:
                continue

            # Extract heading if present
            heading_match = re.match(r'^(#{1,3})\s+(.+)$', sec_text, re.MULTILINE)
            heading = heading_match.group(2).strip() if heading_match else "General"

            if len(sec_text) <= max_chunk_size:
                chunks.append({
                    "index": chunk_idx,
                    "heading": heading,
                    "text": sec_text
                })
                chunk_idx += 1
            else:
                # Subdivide paragraph-by-paragraph
                paragraphs = sec_text.split("\n\n")
                current_chunk = []
                current_len = 0
                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    if current_len + len(p) > max_chunk_size and current_chunk:
                        chunk_content = "\n\n".join(current_chunk)
                        chunks.append({
                            "index": chunk_idx,
                            "heading": heading,
                            "text": chunk_content
                        })
                        chunk_idx += 1
                        current_chunk = [p]
                        current_len = len(p)
                    else:
                        current_chunk.append(p)
                        current_len += len(p) + 2

                if current_chunk:
                    chunks.append({
                        "index": chunk_idx,
                        "heading": heading,
                        "text": "\n\n".join(current_chunk)
                    })
                    chunk_idx += 1

        return chunks

    def index_document(
        self,
        project_id: str,
        doc_id: str,
        title: str,
        kind: str,
        content: str
    ) -> Dict[str, Any]:
        """Indexes document chunks into project ChromaDB collection."""
        col = self.get_collection(project_id)
        chunks = self.chunk_document(content)
        if not chunks:
            return {"indexed": 0, "status": "empty"}

        if not col:
            # Fallback in-memory indexing marker
            return {"indexed": len(chunks), "status": "memory_fallback"}

        ids = []
        documents = []
        metadatas = []

        for ch in chunks:
            chunk_id = f"{doc_id}_{ch['index']}"
            ids.append(chunk_id)
            documents.append(ch["text"])
            metadatas.append({
                "project_id": project_id,
                "doc_id": doc_id,
                "title": title,
                "kind": kind,
                "heading": ch["heading"],
                "chunk_index": ch["index"]
            })

        try:
            col.upsert(ids=ids, documents=documents, metadatas=metadatas)
            return {
                "indexed": len(ids),
                "collection": col.name,
                "status": "success",
                "doc_id": doc_id,
                "title": title
            }
        except Exception as exc:
            print(f"[RAG Vector Store] Upsert error: {exc}")
            return {"indexed": 0, "status": "error", "error": str(exc)}

    def query_context(
        self,
        query: str,
        project_id: str,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Queries the vector database for semantically relevant chunks."""
        col = self.get_collection(project_id)
        if not col:
            return []

        try:
            res = col.query(
                query_texts=[query],
                n_results=min(top_k, max(1, col.count())),
                include=["documents", "metadatas", "distances"]
            )
            hits = []
            if res and res.get("documents") and res["documents"][0]:
                for doc_text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                    hits.append({
                        "content": doc_text,
                        "metadata": meta,
                        "similarity": round(1.0 - float(dist), 3) if dist is not None else 1.0,
                        "title": meta.get("title", "Project Document"),
                        "doc_id": meta.get("doc_id", "DOC"),
                        "heading": meta.get("heading", "")
                    })
            return hits
        except Exception as exc:
            print(f"[RAG Vector Store] Query error: {exc}")
            return []

    def get_unified_grounding(
        self,
        project_id: str,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes multi-database grounding context:
        - ChromaDB semantic document vectors
        - SQLite project specifications & documents
        - Codebase AST public endpoints
        - Active quality gates
        """
        grounding = {
            "projectId": project_id,
            "vectorHits": [],
            "documents": [],
            "endpoints": [],
            "gatesCount": 0
        }

        # 1. Query ChromaDB Vector Store
        if query:
            grounding["vectorHits"] = self.query_context(query, project_id, top_k=4)

        # 2. Query SQLite Governed Documents
        from backend.db import db
        try:
            with db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, title, kind, current_version, status, updated_at FROM documents WHERE project_id = ? ORDER BY updated_at DESC LIMIT 10",
                    (project_id,)
                )
                grounding["documents"] = [
                    {
                        "id": row[0],
                        "title": row[1],
                        "kind": row[2],
                        "version": row[3],
                        "status": row[4],
                        "updated_at": row[5]
                    }
                    for row in cur.fetchall()
                ]
                cur.execute("SELECT COUNT(*) FROM quality_gates WHERE project_id = ?", (project_id,))
                row = cur.fetchone()
                grounding["gatesCount"] = row[0] if row else 0
        except Exception as e:
            print(f"[RAG Grounding] DB query error: {e}")

        # 3. Check for AST manifest
        ast_path = Path("data") / "projects" / project_id / "ast_discovery.json"
        if ast_path.is_file():
            try:
                ast_data = json.loads(ast_path.read_text(encoding="utf-8"))
                grounding["endpoints"] = ast_data.get("endpoints", [])[:8]
            except Exception:
                pass

        return grounding


# Global singleton instance
rag_store = RAGVectorStore()
