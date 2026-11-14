"""Hybrid retrieval over a project's indexed documents: PostgreSQL full-text plus pgvector, merged by reciprocal rank fusion.

`retrieve(project_id, question, k)` is what a QE stage calls: it returns the top `k` chunks, each with its citation. Without
embeddings (no pgvector, or no embeddings API) the result is the keyword ranking alone and `mode()` says so.
"""
from __future__ import annotations

import re

from backend.rag import embed, store

CANDIDATES = 20  # fused candidates; the model rerank (rerank.py) cuts them to the top k
RRF_K = 60
WORD = re.compile(r"[A-Za-z0-9_]{3,}")


def tsquery(question: str) -> str:
    """Words OR-ed (a natural question rarely matches every word); only [A-Za-z0-9_] reaches the query, so it cannot hold operators."""
    words = list(dict.fromkeys(w.lower() for w in WORD.findall(question)))
    return " | ".join(words)


def citation(row: dict) -> dict:
    return {"doc_id": row["doc_id"], "document": row["filename"], "version": row["version"], "section": row["section"], "page": row["page"],
            "line_start": row["line_start"], "line_end": row["line_end"], "source_path": row["source_path"]}


def fuse(rankings: dict[str, list[dict]]) -> list[dict]:
    """Reciprocal rank fusion: each list gives a chunk 1/(60+rank); chunks seen by both lists rise."""
    merged: dict[str, dict] = {}
    for via, ranked in rankings.items():
        for rank, row in enumerate(ranked, 1):
            hit = merged.setdefault(row["id"], {**row, "score": 0.0, "via": []})
            hit["score"] += 1 / (RRF_K + rank)
            hit["via"].append(via)
    return sorted(merged.values(), key=lambda r: (-r["score"], r["doc_id"], r["line_start"]))


def mode(project_id: str) -> dict:
    """What search can do for this project: keyword always; vector only when every indexed document has embeddings."""
    found = store.sources(project_id)
    vector = bool(found) and all(s["embedded"] == s["chunk_count"] for s in found)
    reasons = [s["embed_note"] for s in found if s["embed_note"]]
    return {"keyword": True, "vector": vector, "documents": len(found),
            "note": "" if vector or not found else (reasons[0] if reasons else "No embeddings are stored, so search is keyword only.")}


def candidates(project_id: str, question: str, limit: int = CANDIDATES) -> list[dict]:
    rankings: dict[str, list[dict]] = {}
    if query := tsquery(question):
        rankings["keyword"] = store.keyword(project_id, query, limit)
    if mode(project_id)["vector"]:
        vectors, _ = embed.embed([question])
        if vectors:
            rankings["vector"] = store.nearest(project_id, vectors[0], limit)
    return fuse(rankings)[:limit]


def result(row: dict) -> dict:
    return {"id": row["id"], "text": row["body"], "score": round(row["score"], 5), "via": row["via"], "citation": citation(row)}


def retrieve(project_id: str, question: str, k: int = 8) -> list[dict]:
    """The top k chunks for a question, best first: {id, text, score, via, citation}. Empty when nothing matches."""
    return [result(r) for r in candidates(project_id, question)[:k]]
