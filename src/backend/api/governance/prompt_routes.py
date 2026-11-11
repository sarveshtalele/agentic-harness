"""Prompt versions."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core import auth, prompts

router = APIRouter()

class PromptIn(BaseModel):
    body: str = Field(min_length=10)
    note: str = Field(min_length=1)


@router.get("/api/prompts")
def list_prompts():
    return prompts.list_all()


@router.get("/api/prompts/{agent}")
def prompt_history(agent: str):
    items = prompts.history(agent)
    if not items:
        raise HTTPException(404, f"Prompt history not found for agent: {agent}")
    names = auth.display_names({i["author"] for i in items})
    return [{**i, "author_name": names.get(i["author"], i["author"])} for i in items]


@router.post("/api/prompts/{agent}", status_code=201)
def add_prompt_version(agent: str, body: PromptIn):
    return prompts.add_version(agent, body.body, body.note, auth.signer())


@router.post("/api/prompts/{agent}/activate/{version}")
def activate_prompt(agent: str, version: int):
    return prompts.activate(agent, version)
