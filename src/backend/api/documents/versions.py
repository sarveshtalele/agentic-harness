"""Documents API: versions, diff, restore and approve."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from backend.api.documents.crud import _named
from backend.core import auth, documents

router = APIRouter()


@router.get("/api/documents/{doc_id}/versions")
def document_versions(doc_id: str):
    return _named(documents.versions(doc_id))


@router.get("/api/documents/{doc_id}/diff", response_class=PlainTextResponse)
def document_diff(doc_id: str, a: int, b: int):
    return documents.diff(doc_id, a, b)


@router.post("/api/documents/{doc_id}/restore/{version}")
def restore_document(doc_id: str, version: int):
    return documents.restore(doc_id, version, auth.signer())


@router.post("/api/documents/{doc_id}/approve")
def approve_document(doc_id: str):
    return documents.set_status(doc_id, "approved", auth.signer())
