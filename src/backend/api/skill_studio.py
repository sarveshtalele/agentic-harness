"""Skill Creator Studio API (plan M3). Every rule is enforced here or in core/skill_studio, not only in the UI.

Writes, tests, evaluations, publishing and uploads need the admin or a ba, developer or qe_lead account. Delete is admin only.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field, ValidationError

from backend.core import documents
from backend.core.skill_studio import access, author, plans, steps, testing, versions
from backend.core.skill_studio import source as sources
from backend.core.skill_studio.models import plan_schema

router = APIRouter(prefix="/api/skill-studio")

@contextmanager
def _refusals():
    try:
        yield
    except (plans.PlanStateError, versions.PublishRefused) as exc:
        raise HTTPException(409, str(exc)) from exc
    except sources.SourceError as exc:
        raise HTTPException(400, str(exc)) from exc
    except testing.ProfileRefused as exc:
        raise HTTPException(403, str(exc)) from exc
    except author.ReplyRejected as exc:
        raise HTTPException(502, {"message": exc.message, "reply_file": exc.reply_file}) from exc


@router.get("/documents")
def list_documents(project_id: str):
    access.project(project_id, write=False)
    return {"documents": [{k: d[k] for k in ("id", "project_id", "kind", "title", "current_version", "status", "updated_at")} for d in documents.list_for(project_id)]}


@router.post("/sources/parse")
async def parse_source(file: UploadFile = File(...)):
    access.author()
    blob = await file.read(sources.MAX_SOURCE_CHARS * 8 + 1)
    with _refusals():
        if len(blob) > sources.MAX_SOURCE_CHARS * 8:
            raise sources.SourceError("The file is too large for a skill source.")
        found = sources.resolve({"type": "upload", "text": sources.parse_upload(blob, file.filename or "upload.md"), "filename": file.filename})
    return {"text": found["text"], "sha256": found["sha256"], "filename": found["ref"], "chars": len(found["text"])}


class SourceIn(BaseModel):
    type: Literal["document", "upload", "text"]
    document_id: str | None = None
    text: str | None = None
    filename: str | None = None


class PlanIn(BaseModel):
    project_id: str
    kind: Literal["instructions", "scripts"]
    source: SourceIn
    request: str = Field(default="", max_length=4000)
    revise: str = ""  # the name of an existing skill this plan revises


@router.post("/plans", status_code=201)
async def create_plan(body: PlanIn):
    with _refusals():
        return await steps.propose(body.project_id, body.kind, body.request, body.source.model_dump(), body.revise)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    return access.plan(plan_id, write=False)


class PlanEdit(BaseModel):
    plan: dict


@router.patch("/plans/{plan_id}")
def edit_plan(plan_id: str, body: PlanEdit):
    user, current = access.author(), access.plan(plan_id)
    full = plans.get(plan_id, with_source=True)
    taken = author._skill_names()
    try:
        plan = plan_schema(current["kind"], taken, full["source_text"], current["revise"]).model_validate(body.plan)
    except ValidationError as exc:
        raise HTTPException(422, "; ".join(f"{'.'.join(map(str, e['loc'])) or 'plan'}: {e['msg']}" for e in exc.errors()[:8])) from None
    with _refusals():
        return plans.update(plan_id, plan, user["id"])


@router.post("/plans/{plan_id}/approve")
def approve_plan(plan_id: str):
    user = access.author()
    access.plan(plan_id)
    with _refusals():
        return plans.approve(plan_id, user["id"])


@router.post("/plans/{plan_id}/generate")
async def generate(plan_id: str):
    user = access.author()
    access.plan(plan_id)
    with _refusals():
        return await steps.generate(plan_id, user["id"])


class TestIn(BaseModel):
    mode: Literal["scripts", "sample"] = "scripts"
    sample_text: str | None = Field(default=None, max_length=sources.MAX_SOURCE_CHARS)
    document_id: str | None = None


@router.post("/plans/{plan_id}/test")
async def run_test(plan_id: str, body: TestIn):
    current = access.plan(plan_id)
    with _refusals():
        if body.mode == "scripts":
            testing.check_profile()
            if current["kind"] != "scripts":
                raise plans.PlanStateError("An instructions skill has no scripts to run. Use mode sample.")
            return testing.run_pytest(plans.require_generated(plan_id)[1])
        sample = body.sample_text or ""
        if body.document_id:
            try:
                sample = sources.visible_document(body.document_id)["content"]
            except KeyError:
                raise HTTPException(404, "Document not found") from None
        if not sample.strip():
            raise sources.SourceError("Give sample_text or a document_id to try the skill on.")
        return await steps.try_sample(plan_id, sample)


@router.post("/plans/{plan_id}/evaluate")
async def evaluate(plan_id: str):
    user = access.author()
    access.plan(plan_id)
    with _refusals():
        return await steps.evaluate(plan_id, user["id"])


@router.post("/plans/{plan_id}/publish", status_code=201)
def publish(plan_id: str):
    user = access.author()
    access.plan(plan_id)
    with _refusals():
        current, folder = plans.require_generated(plan_id)
        return versions.publish(current["plan"]["name"], folder, author=user["id"], project_id=current["project_id"], plan_id=plan_id,
                                prompt_ref=f"{current['prompt_ref']}+draft:{current['draft_sha256'][:12]}")


@router.get("/skills/{name}/versions")
def list_versions(name: str):
    return {"name": name, "versions": versions.history(name)}


@router.get("/skills/{name}/versions/{version}/zip")
def download(name: str, version: int):
    try:
        blob = versions.zip_of(name, version)
    except KeyError:
        raise HTTPException(404, f"No version {version} of {name}") from None
    return Response(blob, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}-v{version}.zip"'})


@router.post("/upload", status_code=201)
async def upload(project_id: str = Form(...), file: UploadFile = File(...)):
    user = access.author()
    access.project(project_id, write=True)
    blob = await file.read(versions.MAX_ZIP_BYTES + 1)
    with _refusals():
        return versions.upload(blob, author=user["id"], project_id=project_id)


@router.delete("/skills/{name}")
def delete(name: str, project_id: str):
    user = access.author(admin_only=True)
    access.project(project_id, write=True)
    with _refusals():
        try:
            return versions.delete(name, by=user["id"], project_id=project_id)
        except KeyError:
            raise HTTPException(404, f"Skill not found: {name}") from None

