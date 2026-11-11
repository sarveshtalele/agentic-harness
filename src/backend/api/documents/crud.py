"""Documents API: list, create, read, save and delete."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.core import auth, documents, files, gates
from backend.db import db, rows

router = APIRouter()


class DocIn(BaseModel):
    kind: str = "brd"
    title: str = Field(min_length=1)
    content: str = ""
    template_id: str | None = None


class VersionIn(BaseModel):
    content: str
    note: str = ""


def _named(items: list[dict]) -> list[dict]:
    names = auth.display_names({i["author"] for i in items})
    return [{**i, "author_name": names.get(i["author"], i["author"])} for i in items]


@router.get("/api/documents")
def all_documents():
    with db() as con:
        projects = rows(con.execute("SELECT id, name FROM projects WHERE archived=0 AND id!='prj_agent_evals'"))
    found = [{**doc, "project": p["name"]} for p in projects if auth.can_see_project(p["id"]) for doc in documents.list_for(p["id"])]
    return sorted(found, key=lambda doc: doc["updated_at"], reverse=True)[:500]


@router.get("/api/projects/{project_id}/documents")
def list_documents(project_id: str, kind: str | None = None):
    _project(project_id)
    return documents.list_for(project_id, kind)


@router.post("/api/projects/{project_id}/documents", status_code=201)
def create_document(project_id: str, body: DocIn):
    _project(project_id)
    content = body.content or (files.get_template(body.template_id)["body"] if body.template_id else "")
    return documents.create(project_id, body.kind, body.title, content, auth.signer(), template_id=body.template_id)


@router.get("/api/documents/{doc_id}")
def get_document(doc_id: str, version: int | None = None):
    doc = documents.get(doc_id, version)
    return {**_named([doc])[0], "would_reopen": gates.would_reopen(doc["project_id"], doc["kind"])}


@router.put("/api/documents/{doc_id}")
def save_document(doc_id: str, body: VersionIn):
    return documents.save_version(doc_id, body.content, auth.signer(), note=body.note or "Edited")


@router.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str):
    documents.delete(doc_id, auth.signer())
    return Response(status_code=204)
