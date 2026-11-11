"""Documents API: export as md, docx, feature, patch, csv or jira, and embedded images."""
from __future__ import annotations

import asyncio
import csv
import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from backend.core import auth, documents, files
from backend.core.security import safe_path

router = APIRouter()


@router.get("/api/documents/{doc_id}/export/{fmt}")
def export_document(doc_id: str, fmt: str, version: int | None = None):
    doc = documents.get(doc_id, version)
    slug = "".join(c if c.isalnum() else "-" for c in doc["title"]).strip("-").lower()[:60] or doc["id"]
    name = f"{slug}-v{doc['version']}"
    if fmt == "md":
        return Response(doc["content"], media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}.md"'})
    if fmt == "feature":
        return Response(doc["content"], media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}.feature"'})
    if fmt == "docx":
        body = doc["content"] if doc["kind"] != "gherkin" else f"```\n{doc['content']}\n```"
        blob = files.markdown_to_docx(doc["title"], body, f"Version {doc['version']} · {doc['status']} · SHA-256 {doc['sha256'][:16]}", documents.image_root(doc))
        return Response(blob, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{name}.docx"'})
    if fmt == "patch":
        return Response(doc["content"], media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}.patch"'})
    if fmt in {"csv", "jira"} and doc["kind"] == "test_cases":
        return Response(_cases_csv(doc["data"], fmt), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}-{fmt}.csv"'})
    raise HTTPException(400, "Use md, docx, feature, patch, or for test cases csv and jira")


@router.post("/api/documents/{doc_id}/images", status_code=201)
async def add_image(doc_id: str, file: UploadFile = File(...)):
    blob = await file.read(documents.MAX_IMAGE_BYTES + 1)
    name = await asyncio.to_thread(documents.save_image, doc_id, blob, auth.signer())
    return {"file": name, "url": f"/api/documents/{doc_id}/images/{name}"}


@router.get("/api/documents/{doc_id}/images/{name}")
def get_image(doc_id: str, name: str):
    target = safe_path(documents.image_root(documents.get(doc_id)), name)
    if target.suffix not in {".png", ".jpg", ".gif", ".webp"} or not target.is_file():
        raise HTTPException(404, "Image not found")
    media = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}[target.suffix]
    return Response(target.read_bytes(), media_type=media, headers={"X-Content-Type-Options": "nosniff"})


def _cases_csv(cases: list[dict], fmt: str) -> str:
    def cell(value) -> str:  # spreadsheets execute cells starting with these characters
        text = str(value)
        return "'" + text if text[:1] in {"=", "+", "-", "@", "\t", "\r"} else text

    out = io.StringIO()
    writer = csv.writer(out)
    if fmt == "csv":
        writer.writerow(["TC ID", "User Story ID", "Scenario", "Type", "Precondition", "Test Data", "Steps", "Expected Result", "Priority", "Automation Candidate", "Remarks"])
        for c in cases:
            steps = " ".join(f"{i + 1}. {s}" for i, s in enumerate(c["steps"]))
            writer.writerow([cell(v) for v in (c["id"], c["requirement_id"], c["scenario"], c["type"], c["precondition"], c["test_data"], steps, c["expected_result"], c["priority"], f"Yes ({c['level']})", f"Oracle: {c['oracle']}")])
    else:
        writer.writerow(["Summary", "Issue Type", "Description", "Priority", "Labels", "Parent/Story ID"])
        for c in cases:
            description = f"Steps: {' '.join(c['steps'])}\nExpected: {c['expected_result']}"
            writer.writerow([cell(v) for v in (f"{c['id']}: {c['scenario']}", "Test", description, c["priority"], c["type"].replace(" ", "-"), c["requirement_id"])])
    return out.getvalue()
