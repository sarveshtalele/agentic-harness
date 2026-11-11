"""Documents API: independent review and agent refinement."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.core import doc_checks, documents, files
from backend.maf import runtime as agents
from backend.maf import workflows

router = APIRouter()


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
