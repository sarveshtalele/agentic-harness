"""Projects API: members and ownership transfer."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.api.projects.crud import get_project
from backend.core import auth

router = APIRouter()


class MemberIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    role: str = "developer"


class TransferIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)


@router.get("/api/projects/{project_id}/members")
def list_members(project_id: str):
    _project(project_id)
    return auth.members(project_id)


@router.post("/api/projects/{project_id}/members", status_code=201)
def add_member(project_id: str, body: MemberIn):
    """The owner types the exact username. The answer is added or not found, and nothing else about the account."""
    _project(project_id)
    try:
        auth.add_member(project_id, body.username, body.role)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "No account has that username") from exc
    return auth.members(project_id)


@router.delete("/api/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(project_id: str, user_id: str):
    _project(project_id)
    auth.remove_member(project_id, user_id)
    return Response(status_code=204)


@router.post("/api/projects/{project_id}/transfer")
def transfer(project_id: str, body: TransferIn):
    _project(project_id)
    try:
        auth.transfer_project(project_id, body.username)
    except KeyError as exc:
        raise HTTPException(404, "No account has that username") from exc
    return get_project(project_id)
