"""Documents API: BRD generation from a template."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.common import _project
from backend.api.documents.brd import default_content
from backend.core import auth, documents, files, ledger
from backend.db import db, now, row
from backend.repos.doc_parser import parse_document

router = APIRouter()


class GenerateBRDIn(BaseModel):
    template_id: str | None = None
    title: str | None = None
    sections: list[dict] | None = None
    variables: dict | None = None
    context: str | None = None
    instructions: str | None = None


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
            content = default_content(heading, project)

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
