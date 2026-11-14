"""Requirement documents for retrieval (QE v2 step 4): several uploads per project, a list, retrieval and a cited answer."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.core.source_text import UnsupportedFile
from backend.rag import analyst, ingest, retrieve, store

router = APIRouter()


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=8, ge=1, le=20)
    rerank: bool = False  # one model call that picks the best k of the 20 candidates


@router.post("/api/projects/{project_id}/rag/documents", status_code=201)
async def upload(project_id: str, files: list[UploadFile] = File(...)):
    """Several files at once; each is indexed or refused on its own, and the answer lists both."""
    _project(project_id)
    done, refused = [], []
    for item in files:
        blob = await item.read()
        try:
            done.append(await asyncio.to_thread(ingest.add, project_id, item.filename or "", blob))
        except UnsupportedFile as exc:
            refused.append({"filename": item.filename, "error": str(exc)})
    if not done:
        raise HTTPException(400, "; ".join(r["error"] for r in refused) or "No file was sent")
    return {"indexed": done, "refused": refused, "search": retrieve.mode(project_id)}


@router.get("/api/projects/{project_id}/rag")
def status(project_id: str):
    """The indexed documents and what search can do (keyword always; vector only with pgvector and an embeddings API)."""
    _project(project_id)
    return {"documents": store.sources(project_id), "search": retrieve.mode(project_id)}


@router.post("/api/projects/{project_id}/rag/retrieve")
async def find(project_id: str, body: Question):
    _project(project_id)
    chunks = await analyst.retrieve_reranked(project_id, body.question, body.k) if body.rerank else retrieve.retrieve(project_id, body.question, body.k)
    return {"chunks": chunks, "search": retrieve.mode(project_id)}


@router.post("/api/projects/{project_id}/rag/ask")
async def ask(project_id: str, body: Question):
    _project(project_id)
    return {**await analyst.ask(project_id, body.question, body.k), "search": retrieve.mode(project_id)}
