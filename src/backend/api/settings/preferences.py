"""Which roles sign each gate, and the usage time zone."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import auth, models

router = APIRouter()

class GateRolesIn(BaseModel):
    roles: dict[str, list[str]]


class ZoneIn(BaseModel):
    timezone: str


@router.get("/api/settings/gate-roles")
def get_gate_roles():
    """Which roles may sign each gate. A gate not listed may be signed by anyone who can write."""
    return {"roles": {str(g): r for g, r in auth.gate_roles().items()}, "assignable": [r for r in auth.ROLES if r != "viewer"]}


@router.put("/api/settings/gate-roles")
def put_gate_roles(body: GateRolesIn):
    try:
        auth.set_gate_roles(body.roles)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc)) from exc
    return get_gate_roles()


@router.get("/api/settings/timezone")
def get_timezone():
    return {"timezone": models.timezone_name()}


@router.put("/api/settings/timezone")
def set_timezone(body: ZoneIn):
    try:
        return {"timezone": models.set_timezone(body.timezone)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
