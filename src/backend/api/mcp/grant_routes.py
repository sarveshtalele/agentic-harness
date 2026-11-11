"""Grants: which role may call which MCP tool. Every route here is admin-only."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.api.mcp.common import answered, require_admin
from backend.core.mcp import grants

router = APIRouter()


class GrantIn(BaseModel):
    server_id: str = Field(..., min_length=1)
    tool_name: str = Field(..., min_length=1, max_length=200)  # a listed tool's name, or * for all of them
    role: str


@router.get("/grants")
def list_grants(server_id: Optional[str] = None):
    require_admin()
    return {"grants": grants.listing(server_id), "roles": list(grants.GRANT_ROLES)}


@router.post("/grants", status_code=201)
def add_grant(body: GrantIn):
    user = require_admin()
    with answered():
        return grants.add(body.server_id, body.tool_name, body.role, user["id"])


@router.delete("/grants/{grant_id}")
def delete_grant(grant_id: str):
    require_admin()
    grants.remove(grant_id)
    return {"deleted": True, "id": grant_id}
