"""Plugins API: what is installed, what MAF loaded from it, which skills are slash commands, the MCP servers it declares.

Listing is for every signed-in user. Install, enable, disable, grants and MCP registration are admin-only.
"""
from __future__ import annotations

from pathlib import Path

from agent_framework import FileSkillsSource, SkillsSourceContext
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.api.mcp.common import answered, require_admin
from backend.core import auth, plugin_grants, plugin_install
from backend.core import plugins as plugin_lib
from backend.core.mcp import registry
from backend.core.skills import _run

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


def _describe(plugin: plugin_lib.Plugin) -> dict:
    loaded, failed, commands = 0, [], []
    if plugin.skills_dir:
        got = {Path(s.path).resolve() for s in _run(FileSkillsSource([plugin.skills_dir]).get_skills(SkillsSourceContext(agent=None)))}
        loaded = len(got)
        failed = [f"{md.parent.name}: MAF could not load it" for md in sorted(plugin.skills_dir.glob("*/SKILL.md")) if md.parent.resolve() not in got]
        commands = sorted(plugin_lib.command_skill_names(plugin.skills_dir))
    servers = [{"name": s["name"], "transport": s["transport"], "command": s["command"], "args": s["args"], "url": s["url"],
                "secret_names": sorted((s["env"] if s["transport"] == "stdio" else s["headers"]) or {})} for s in plugin.mcp_servers]
    return {"id": plugin.id, "version": plugin.version, "description": plugin.description, "trust": plugin.trust, "source": plugin.source,
            "manifest": plugin.manifest, "problems": plugin.problems, "skills": loaded, "commands": commands, "skill_problems": failed,
            "enabled": plugin.enabled, "mcp_servers": servers}


def _plugin(plugin_id: str) -> plugin_lib.Plugin:
    found = next((p for p in plugin_lib.discover() if p.id == plugin_id), None)
    if not found:
        raise KeyError(f"plugin {plugin_id}")
    return found


@router.get("")
def list_plugins() -> list[dict]:
    return [_describe(p) for p in plugin_lib.discover()]


@router.get("/slash")
def slash_menu() -> list[dict]:
    """Commands and skills of enabled plugins for the chat "/" menu, limited to the plugins the user's role was granted."""
    role = plugin_grants.role_of(auth.current_user.get())
    return [{k: v for k, v in e.items() if k != "path"} for e in plugin_lib.slash_entries(role=role)]


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...)):
    require_admin()
    data = await file.read(plugin_install.MAX_ZIP + 1)
    try:
        with answered():
            return _describe(plugin_install.install_zip(data))
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc


def _toggle(plugin_id: str, enabled: bool) -> dict:
    user = require_admin()
    with answered():
        plugin_lib.set_enabled(plugin_id, enabled, user["id"])
    return _describe(_plugin(plugin_id))


@router.post("/{plugin_id}/enable")
def enable(plugin_id: str):
    return _toggle(plugin_id, True)


@router.post("/{plugin_id}/disable")
def disable(plugin_id: str):
    return _toggle(plugin_id, False)


@router.post("/{plugin_id}/mcp/register")
def register_mcp(plugin_id: str):
    """Register the plugin's .mcp.json servers as not_connected. A server this plugin already registered is skipped."""
    user = require_admin()
    plugin = _plugin(plugin_id)
    have = {s["name"] for s in registry.all_servers() if s["plugin_id"] == plugin_id}
    registered, skipped, refused = [], [], []
    for spec in plugin.mcp_servers:
        if spec["name"] in have:
            skipped.append(spec["name"])
            continue
        try:
            registered.append(registry.public(registry.add(spec, owner=user["id"], plugin_id=plugin_id), []))
        except registry.McpProblem as exc:
            refused.append({"name": spec["name"], "status": exc.status, "message": exc.message})
    return {"plugin_id": plugin_id, "registered": registered, "skipped": skipped, "refused": refused}


class GrantIn(BaseModel):
    role: str


@router.get("/{plugin_id}/grants")
def list_grants(plugin_id: str):
    """Every signed-in user may read a plugin's grants; no grant means every role may use it."""
    _plugin(plugin_id)
    return {"plugin_id": plugin_id, "grants": plugin_grants.listing(plugin_id), "roles": list(auth.ROLES)}


@router.post("/{plugin_id}/grants", status_code=201)
def add_grant(plugin_id: str, body: GrantIn):
    user = require_admin()
    _plugin(plugin_id)
    with answered():
        return plugin_grants.add(plugin_id, body.role, user["id"])


@router.delete("/{plugin_id}/grants/{grant_id}")
def delete_grant(plugin_id: str, grant_id: str):
    user = require_admin()
    plugin_grants.remove(plugin_id, grant_id, user["id"])
    return {"deleted": True, "id": grant_id}
