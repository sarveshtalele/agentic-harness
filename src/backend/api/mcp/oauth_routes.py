"""OAuth sign-in to a remote MCP server, one member at a time (R4): start, the provider's callback, status, sign-out."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from backend import config
from backend.api.mcp.common import answered
from backend.core import auth
from backend.core.mcp import oauth, registry
from backend.core.mcp.registry import McpProblem

router = APIRouter()
CALLBACK = "/api/mcp/oauth/callback"  # public (backend/app.py): the provider's redirect is a cross-site navigation without our cookie


class StartIn(BaseModel):
    return_to: str = Field("/", max_length=300)


def redirect_uri(request: Request) -> str:
    """The browser-facing address of the callback: the page's origin (checked against the allowed origins), else ours."""
    origin = request.headers.get("origin", "")
    base = origin if origin in config.ALLOWED_ORIGINS else str(request.base_url).rstrip("/")
    return f"{base}{CALLBACK}"


def start_for(server_id: str, request: Request, return_to: str) -> dict:
    user = auth.current_user.get()
    with answered():
        return {"url": oauth.start(server_id, user["id"], redirect_uri(request), return_to)}


@router.post("/servers/{server_id}/oauth/start")
def start(server_id: str, body: StartIn, request: Request):
    return start_for(server_id, request, body.return_to)


@router.get("/servers/{server_id}/oauth")
def status(server_id: str):
    registry.get(server_id)
    return {"connected": oauth.connected(server_id, auth.current_user.get()["id"])}


@router.delete("/servers/{server_id}/oauth")
def sign_out(server_id: str):
    oauth.disconnect(server_id, auth.current_user.get()["id"])
    return {"connected": False}


@router.get("/oauth/callback")
def callback(state: str = "", code: str = "", error: str = ""):
    if error or not state or not code:
        return PlainTextResponse(f"The sign-in was not completed ({error or 'no code returned'}). Close this tab and try Connect again.", status_code=400)
    try:
        server_id, return_to = oauth.finish(state, code)
    except McpProblem as exc:
        return PlainTextResponse(exc.message, status_code=exc.status)
    return RedirectResponse(f"{return_to}{'&' if '?' in return_to else '?'}connected={server_id}", status_code=303)
