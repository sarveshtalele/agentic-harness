"""Documents API: upload a custom BRD template and register its structure."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.api.common import _project
from backend.core import auth, documents, ledger
from backend.core.security import sha256
from backend.db import db, new_id, now
from backend.repos.doc_parser import parse_document

router = APIRouter()


@router.post("/api/projects/{project_id}/templates/upload", status_code=201)
async def upload_project_template(
    project_id: str,
    file: UploadFile = File(...),
):
    """Upload custom BRD template (.md, .docx, .txt, .pdf), parse structure, and register it."""
    _project(project_id)
    blob = await file.read()
    if not blob:
        raise HTTPException(400, "Uploaded template file is empty")

    parsed = parse_document(blob, file.filename or "template.md")
    template_name = parsed["title"] or Path(file.filename or "template").stem
    template_id = new_id("tpl")
    body_content = parsed["raw_text"]
    digest = sha256(body_content)
    stamp = now()

    # Save into templates database
    with db() as con:
        con.execute(
            "INSERT INTO templates (id, project_id, name, kind, body, builtin, sha256, created_at) "
            "VALUES (?, ?, ?, 'brd', ?, 0, ?, ?)",
            (template_id, project_id, template_name, body_content, digest, stamp)
        )

    # Save as a template document in documents
    doc = documents.create(
        project_id,
        "template",
        template_name,
        body_content,
        auth.signer(),
        template_id=template_id
    )

    # Emit notification event to ledger
    ledger.append(
        project_id,
        auth.signer(),
        "template.uploaded",
        template_id,
        {
            "title": template_name,
            "filename": file.filename,
            "sections_count": len(parsed["sections"]),
            "placeholders": parsed.get("placeholders", [])
        }
    )

    headings = [s.get("heading", "") for s in parsed.get("sections", []) if isinstance(s, dict)]
    return {
        "template_id": template_id,
        "document_id": doc["id"],
        "title": template_name,
        "name": template_name,
        "headings": headings,
        "sections": parsed["sections"],
        "tables": parsed["tables"],
        "raw_text": body_content,
        "placeholders": parsed.get("placeholders", []),
        "filename": file.filename,
    }
