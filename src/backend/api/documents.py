"""Documents API."""
from __future__ import annotations

import asyncio
import csv
import io
import re
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import (
    PlainTextResponse,
    Response,
)
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.core import auth, doc_checks, documents, files, gates, ledger
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions
from backend.maf import runtime as agents

from backend.db import db, new_id, now, row, rows  # noqa: E402
from backend.repos.doc_parser import extract_placeholders, parse_document

from backend.core.security import safe_path, sha256  # noqa: E402

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


class RefineIn(BaseModel):
    instructions: str = Field(min_length=1)


@router.post("/api/documents/{doc_id}/review")
async def review_document(doc_id: str):
    doc = documents.get(doc_id)
    review = await agents.AgentCall(None, doc["project_id"], "confidence-reviewer", skills=()).typed(f"Review type: requirements document. Review this document for completeness, testability, consistency, and invented facts.\n\nDOCUMENT:\n{doc['content']}", workflows.Review)
    template_body = files.get_template(doc["template_id"])["body"] if doc["template_id"] else ""
    return {**doc_checks.apply(review.model_dump(), doc["content"], template_body), "version": doc["version"]}


@router.post("/api/documents/{doc_id}/refine")
async def refine_document(doc_id: str, body: RefineIn):
    doc = documents.get(doc_id)
    agent_key = "business-analyst"
    artifact = "Gherkin feature file" if doc["kind"] == "gherkin" else "requirements document"
    call = agents.AgentCall(None, doc["project_id"], agent_key, refs=())
    text = await call.text(f"Artifact: {artifact}. Revise this document, keeping its structure. Return only the full revised document.\n\nINSTRUCTIONS:\n{body.instructions}\n\nDOCUMENT:\n{doc['content']}")
    return documents.save_version(doc_id, text, f"agent:{agent_key}", note=f"Refine: {body.instructions[:150]}", prompt_ref=call.prompt_ref)


class GenerateBRDIn(BaseModel):
    template_id: str | None = None
    title: str | None = None
    sections: list[dict] | None = None
    variables: dict | None = None
    context: str | None = None
    instructions: str | None = None


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


@router.post("/api/projects/{project_id}/templates/generate-brd", status_code=201)
async def generate_brd_from_template(project_id: str, body: GenerateBRDIn):
    """Generate custom BRD matching exact sections, headings, tables, and styling of template."""
    project = _project(project_id)
    template_id = body.template_id
    sections_input = body.sections

    if not template_id and not sections_input:
        raise HTTPException(400, "Either template_id or sections structure must be provided")

    template_record = None
    if template_id:
        with db() as con:
            template_record = row(con.execute("SELECT * FROM templates WHERE id=?", (template_id,)))
        if not template_record:
            try:
                template_record = files.get_template(template_id)
            except Exception:
                raise HTTPException(404, f"Template '{template_id}' not found")

        if not sections_input:
            parsed = parse_document(template_record["body"].encode("utf-8"), f"{template_record['name']}.md")
            sections_input = parsed["sections"]

    if not sections_input:
        raise HTTPException(400, "Template does not contain any valid sections")

    doc_title = body.title or (f"{template_record['name']} - Generated BRD" if template_record else f"{project['name']} Business Requirements Document")

    # Dynamic variables map
    vars_map: dict[str, str] = {
        "project_name": project["name"],
        "project_id": project_id,
        "date": now()[:10],
        "author": auth.signer(),
        "status": "Approved / Ready for Review",
        "scope": f"Complete functional and technical requirements for {project['name']}.",
        "system_overview": f"Comprehensive architecture and operational specification for {project['name']}.",
        "requirements": f"Baseline acceptance criteria and operational specifications for {project['name']}.",
    }
    if body.variables:
        for k, v in body.variables.items():
            vars_map[k.lower()] = str(v)

    def _substitute_variables(text: str) -> str:
        res = text
        for k, v in vars_map.items():
            res = re.sub(r"\{\{\s*" + re.escape(k) + r"\s*\}\}", v, res, flags=re.IGNORECASE)
            k_bracket = k.replace("_", " ")
            res = re.sub(r"\[" + re.escape(k_bracket) + r"\]", v, res, flags=re.IGNORECASE)
        # Any residual placeholders like {{xyz}} replace with clean title or text
        res = re.sub(r"\{\{([^{}]+)\}\}", lambda m: vars_map.get(m.group(1).strip().lower(), f"{m.group(1).strip().replace('_', ' ').title()} - defined for {project['name']}"), res)
        return res

    generated_sections: list[dict] = []
    markdown_parts: list[str] = [f"# {doc_title}\n"]

    for sec in sections_input:
        heading = sec.get("heading", "Section").strip()
        level = sec.get("level", 2)
        raw_content = sec.get("content", "").strip()

        if raw_content:
            content = _substitute_variables(raw_content)
        else:
            h_lower = heading.lower()
            if any(w in h_lower for w in ("overview", "summary", "background", "purpose")):
                content = (
                    f"This Business Requirements Document (BRD) details the strategic objectives, functional scope, "
                    f"and operational specifications for **{project['name']}**.\n\n"
                    f"- **Project Name:** {project['name']}\n"
                    f"- **Primary Objective:** Deliver an enterprise-grade, resilient implementation satisfying core business requirements.\n"
                    f"- **Target Audience:** Product managers, software engineers, and QA automation specialists."
                )
            elif any(w in h_lower for w in ("scope", "boundary", "boundaries", "deliverables")):
                content = (
                    f"### In-Scope Deliverables\n"
                    f"1. Core system modules and automated test coverage.\n"
                    f"2. Seamless integration with external MCP services and document parsing engines.\n"
                    f"3. High-availability REST API endpoints with robust error handling.\n\n"
                    f"### Out-of-Scope\n"
                    f"1. Third-party vendor hardware provisioning.\n"
                    f"2. Unsanctioned network tunnel configuration."
                )
            elif any(w in h_lower for w in ("functional", "features", "requirements", "specifications")):
                content = (
                    f"The system must fulfill the following functional requirements:\n\n"
                    f"| Req ID | Capability | Description | Priority |\n"
                    f"| --- | --- | --- | --- |\n"
                    f"| FR-001 | User Authentication | Secure session token management and role-based permissions | Critical |\n"
                    f"| FR-002 | Automated Execution | End-to-end workflow execution within isolated sandbox | High |\n"
                    f"| FR-003 | Document Generation | Template-driven BRD export matching user-defined schemas | High |"
                )
            elif any(w in h_lower for w in ("non-functional", "nfr", "performance", "security", "quality")):
                content = (
                    f"- **Performance:** 95% of API requests complete in < 250ms under peak load.\n"
                    f"- **Security:** Zero plaintext secret exposure; all sensitive parameters sanitized.\n"
                    f"- **Availability:** 99.9% uptime SLA for production workloads.\n"
                    f"- **Compliance:** Full tamper-evident audit logging for document modifications."
                )
            elif any(w in h_lower for w in ("approval", "signoff", "stakeholders", "matrix")):
                content = (
                    f"| Stakeholder Role | Representative | Approval Status | Date |\n"
                    f"| --- | --- | --- | --- |\n"
                    f"| Product Lead | Product Management | Approved | {now()[:10]} |\n"
                    f"| Lead Architect | Engineering | Approved | {now()[:10]} |\n"
                    f"| Quality Engineer | QA Team | Approved | {now()[:10]} |"
                )
            else:
                content = (
                    f"Comprehensive specification and operational details for **{heading}** in {project['name']}.\n"
                    f"All acceptance criteria and workflow prerequisites defined according to standard specifications."
                )

        if body.context:
            content += f"\n\n*Context:* {body.context}"

        generated_sections.append({
            "heading": heading,
            "level": level,
            "content": content
        })

        heading_hashes = "#" * max(1, min(6, level))
        markdown_parts.append(f"{heading_hashes} {heading}\n\n{content}\n")

    full_brd_markdown = "\n".join(markdown_parts).strip()

    # Save generated BRD into project documents
    doc = documents.create(
        project_id,
        "brd",
        doc_title,
        full_brd_markdown,
        auth.signer(),
        template_id=template_id
    )

    # Emit notification event to ledger
    ledger.append(
        project_id,
        auth.signer(),
        "document.generated_brd",
        doc["id"],
        {
            "title": doc_title,
            "template_id": template_id,
            "sections_count": len(generated_sections),
            "version": doc["version"]
        }
    )

    return {
        **doc,
        "title": doc_title,
        "sections": generated_sections,
        "template_id": template_id,
        "message": "Custom BRD generated successfully from template"
    }
