"""BA Studio's outside sources (docs/PHASE2_PLAN.md R4): Jira and Confluence through the Atlassian remote MCP, the only
outside source, optional. The admin adds the server with OAuth sign-in and grants its tools to roles; each member
connects once. Search and fetch are the server's own tools, chosen from its live tool list by the shape of their inputs
(one required `query`, one required `id`), never by a name written here. An attached item becomes a source with its id,
link and fetch time; attaching it again later stores a new version when its content changed. Content is untrusted data.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.api.mcp.common import answered
from backend.api.mcp.oauth_routes import start_for
from backend.core import auth, ledger
from backend.core.mcp import connect, grants, oauth, registry
from backend.core.security import redact, sha256
from backend.db import db, new_id, now, row

router = APIRouter()


class SearchIn(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)


class AttachIn(BaseModel):
    items: list[dict] = Field(..., min_length=1, max_length=20)


class StartIn(BaseModel):
    return_to: str = Field("/", max_length=300)


def _shaped(tools: list[dict], arg: str) -> str | None:
    """The tool whose only required input is `arg` (search: query, fetch: id)."""
    for tool in tools:
        schema = json.loads(tool["parameters_schema"] or "{}")
        if schema.get("required") == [arg] and (schema.get("properties", {}).get(arg) or {}).get("type") == "string":
            return tool["name"]
    return None


def _sources(user: dict) -> list[dict]:
    found = []
    for server in registry.all_servers():
        if server.get("auth") != "oauth" or server["status"] != registry.CONNECTED:
            continue
        tools = [t for t in registry.tools(server["id"]) if grants.allows(server["id"], t["name"], user)]
        search, fetch = _shaped(tools, "query"), _shaped(tools, "id")
        if search and fetch:
            found.append({"id": server["id"], "name": server["name"], "search_tool": search, "fetch_tool": fetch,
                          "connected": oauth.connected(server["id"], user["id"])})
    return found


def _source(user: dict, server_id: str) -> dict:
    found = next((s for s in _sources(user) if s["id"] == server_id), None)
    if not found:
        raise HTTPException(404, "No outside source with search and fetch is granted to your role here")
    return found


def _text(part: dict) -> str:
    """A text part, unwrapped when the server sent a plain string as structured {"result": "..."} (MCP SDK 2 does)."""
    text = part.get("text") or "" if part.get("type") == "text" else ""
    try:
        wrapped = json.loads(text)
    except ValueError:
        return text
    return wrapped["result"] if isinstance(wrapped, dict) and set(wrapped) == {"result"} and isinstance(wrapped["result"], str) else text


def _items(result: dict) -> list[dict]:
    """The search results the server returned as JSON text: a list, or {"results": [...]}."""
    out = []
    for part in result["content"]:
        try:
            data = json.loads(_text(part))
        except (TypeError, ValueError):
            continue
        for item in data if isinstance(data, list) else data.get("results", []) if isinstance(data, dict) else []:
            if isinstance(item, dict) and item.get("id"):
                out.append({"id": str(item["id"]), "title": redact(str(item.get("title") or item["id"]))[:200], "url": str(item.get("url") or "")})
    return out


@router.get("/api/projects/{project_id}/atlassian")
def listing(project_id: str):
    _project(project_id)
    return {"sources": _sources(auth.current_user.get())}


@router.post("/api/projects/{project_id}/atlassian/{server_id}/connect")
def connect_source(project_id: str, server_id: str, body: StartIn, request: Request):
    _project(project_id)
    _source(auth.current_user.get(), server_id)
    return start_for(server_id, request, body.return_to)


@router.post("/api/projects/{project_id}/atlassian/{server_id}/search")
async def search(project_id: str, server_id: str, body: SearchIn):
    _project(project_id)
    user = auth.current_user.get()
    source = _source(user, server_id)
    with answered():
        result = await connect.call(server_id, source["search_tool"], {"query": body.query}, user)
    if not result["ok"]:
        raise HTTPException(502, f"The search failed: {result['error']}")
    return {"items": _items(result)}


@router.post("/api/projects/{project_id}/atlassian/{server_id}/attach")
async def attach(project_id: str, server_id: str, body: AttachIn):
    _project(project_id)
    user = auth.current_user.get()
    source = _source(user, server_id)
    saved = []
    for item in body.items:
        item_id, title, url = str(item.get("id", ""))[:300], str(item.get("title") or item.get("id"))[:200], str(item.get("url", ""))[:500]
        with answered():
            result = await connect.call(server_id, source["fetch_tool"], {"id": item_id}, user)
        if not result["ok"]:
            raise HTTPException(502, f"Fetching {title} failed: {result['error']}")
        body_text = "\n\n".join(_text(p) for p in result["content"]).strip()
        text = redact(f"Source: {source['name']} {item_id}{f' ({url})' if url else ''}, fetched {now()}\n\n{body_text}")
        digest = sha256(body_text)
        with db() as con:
            existing = row(con.execute("SELECT id FROM sources WHERE project_id=? AND sha256=?", (project_id, digest)))
            source_id = existing["id"] if existing else new_id("src")
            if not existing:
                con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?)", (source_id, project_id, f"{title}.md", digest, text, now()))
        saved.append({"id": source_id, "filename": f"{title}.md", "chars": len(text), "unchanged": bool(existing)})
        ledger.append(project_id, auth.signer(), "source.attached", f"{server_id}/{item_id}", {"source_id": source_id, "unchanged": bool(existing)})
    return {"sources": saved}
