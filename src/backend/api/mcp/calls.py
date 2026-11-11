"""Connect (admin) and call (granted roles). Both open a real MCP session through MAF and close it again."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.mcp.common import answered, require_admin
from backend.core import auth, ledger
from backend.core.mcp import connect as mcp_connect, registry
from backend.db import db
from backend.maf.observability import record_tool

router = APIRouter()


class CallIn(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=80)  # the call is audited in this project's ledger
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.post("/servers/{server_id}/connect")
async def connect_server(server_id: str):
    require_admin()
    with answered():
        server = await mcp_connect.connect(server_id)
    return registry.public(server, registry.tools(server_id))


@router.post("/servers/{server_id}/tools/{tool_name}/call")
async def call_tool(server_id: str, tool_name: str, body: CallIn):
    user = auth.current_user.get()
    with db() as con:
        exists = con.execute("SELECT 1 FROM projects WHERE id=?", (body.project_id,)).fetchone()
    if not exists or not auth.can_write(body.project_id, user):
        raise HTTPException(404, "Project not found, or your role there cannot run tools")
    with answered():
        result = await mcp_connect.call(server_id, tool_name, body.arguments, user)
    record_tool(f"user:{user['id']}", body.project_id, None, "mcp_api", f"{server_id}/{tool_name}", body.arguments, result["latency_ms"], result["error"], kind="mcp")
    ledger.append(body.project_id, auth.signer(), "mcp.tool_called", f"{server_id}/{tool_name}", {"ok": result["ok"], "latency_ms": result["latency_ms"], "error": result["error"]})
    if not result["ok"]:
        raise HTTPException(502, f"The MCP server answered with an error: {result['error']}")
    return {"server_id": server_id, "tool": tool_name, **result}
