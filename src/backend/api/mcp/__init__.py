"""MCP API: the server registry, install templates, real connect and call, and per-role grants.

Listing is for every signed-in user. Adding, editing, deleting, connecting and granting are admin-only.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.api.mcp import calls, grant_routes
from backend.api.mcp.common import answered, require_admin
from backend.core.mcp import CONNECTED, grants, registry
from backend.core.mcp.catalog import TEMPLATES

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class ServerIn(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    transport: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list[str]] = None
    url: Optional[str] = None
    env: Optional[dict[str, str]] = None  # stdio only, encrypted at rest, never returned
    headers: Optional[dict[str, str]] = None  # http only, encrypted at rest, never returned


def _shown(server: dict) -> dict:
    return registry.public(server, registry.tools(server["id"]))


@router.get("/catalog")
def catalog():
    """Install templates. None of these is a registered server until an admin adds it."""
    return {"templates": TEMPLATES, "stdio_allowed": registry.stdio_allowed()}


@router.get("/servers")
def list_servers():
    servers = [_shown(s) for s in registry.all_servers()]
    given = grants.listing()
    granted = sum(1 for s in servers for t in s["tools"] if any(g["server_id"] == s["id"] and g["tool_name"] in ("*", t["name"]) for g in given))
    return {"servers": servers, "total_servers": len(servers), "connected_servers": sum(s["status"] == CONNECTED for s in servers),
            "total_tools": sum(s["tools_count"] for s in servers), "authorized_tools": granted,  # listed tools granted to at least one role
            "stdio_allowed": registry.stdio_allowed()}


@router.get("/servers/{server_id}")
def get_server(server_id: str):
    return _shown(registry.get(server_id))


@router.post("/servers", status_code=201)
def add_server(body: ServerIn):
    user = require_admin()
    with answered():
        return _shown(registry.add(body.model_dump(), owner=user["id"]))


@router.patch("/servers/{server_id}")
def edit_server(server_id: str, body: ServerIn):
    require_admin()
    with answered():
        return _shown(registry.edit(server_id, body.model_dump()))


@router.delete("/servers/{server_id}")
def delete_server(server_id: str):
    require_admin()
    registry.delete(server_id)
    return {"deleted": True, "id": server_id}


router.include_router(calls.router)
router.include_router(grant_routes.router)
