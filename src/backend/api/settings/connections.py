"""GitHub connections and the LLM endpoint settings."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.core import auth, models
from backend.maf import llm
from backend.repos import github

router = APIRouter()

class TokenIn(BaseModel):
    token: str = Field(min_length=8)
    label: str = ""


class LLMIn(BaseModel):
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None


@router.get("/api/connections")
def connections():
    return github.list_credentials()


@router.post("/api/connections/github", status_code=201)
async def connect_github(body: TokenIn):
    return await github.connect(body.token.strip(), body.label)


@router.get("/api/connections/{credential_id}/repos")
async def connection_repos(credential_id: str):
    return await github.list_repos(credential_id)


@router.delete("/api/connections/{credential_id}", status_code=204)
def remove_connection(credential_id: str):
    github.delete_credential(credential_id)
    return Response(status_code=204)


@router.get("/api/settings/llm")
def llm_settings():
    if auth.current_user.get()["role"] != "admin":  # only the admin sees the endpoint; a user sees their own model
        mine = auth.describe(auth.current_user.get())
        return {"model": mine["model"] or models.system_default(llm.public()["model"]), "configured": llm.public()["configured"]}
    return llm.public()


@router.put("/api/settings/llm")
@router.post("/api/settings/llm")
def update_llm(body: LLMIn):
    return llm.update(body.base_url, body.model, body.api_key)


@router.post("/api/settings/llm/test")
async def test_llm(body: LLMIn):
    return await llm.test_connection(body.base_url, body.model, body.api_key)
