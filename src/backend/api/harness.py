"""Enterprise QE Harness API Router.
Exposes streaming SSE chat, persistent session management,
58 local machine skills discovery, and MCP tool server integration,
using the centralized platform credentials and project permissions.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.api.common import _project
from backend.config import ROOT
from backend.harness.discovery import LocalSkillDiscovery
from backend.harness.harness_agent import HarnessAgent
from backend.harness.llm_config import LLMConfig
from backend.harness.mcp_manager import MCPClientManager, MCPServerConfig
from backend.harness.project_repository import global_project_repo
from backend.harness.qe_tools import build_qe_tools
from backend.harness.session import AgentSessionManager, SessionState, TodoItem
from backend.maf import llm as platform_llm

router = APIRouter(tags=["harness"])

workspace_dir = str(ROOT)
session_manager = AgentSessionManager()
mcp_manager = MCPClientManager()
skill_discovery = LocalSkillDiscovery(workspace_dir)
harness_agent = HarnessAgent(workspace_dir, skill_discovery=skill_discovery)

active_abort_events: Dict[str, asyncio.Event] = {}


class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: Optional[str] = None
    prompt: Optional[str] = None
    mode: Optional[str] = "plan"
    agentId: Optional[str] = None
    activeAgentId: Optional[str] = None
    systemPrompt: Optional[str] = None
    projectId: Optional[str] = None


class StopRequest(BaseModel):
    sessionId: str


@router.get("/api/harness/config")
async def get_harness_config():
    pub = platform_llm.public()
    return {
        **pub,
        "is_configured": pub.get("configured", False),
    }

@router.get("/api/harness/sessions")
async def list_sessions():
    return {"sessions": session_manager.list_sessions()}


@router.post("/api/harness/sessions")
async def create_session(data: Dict[str, Any] = {}):
    name = data.get("name")
    mode = data.get("mode", "plan")
    project_id = data.get("projectId")
    session = session_manager.create_session(name, mode, project_id=project_id)
    return {"session": session.model_dump()}


@router.get("/api/harness/sessions/{session_id}")
async def get_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.patch("/api/harness/sessions/{session_id}")
async def update_session(session_id: str, data: Dict[str, Any]):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if "mode" in data:
        session.mode = data["mode"]
    if "activeAgentId" in data:
        session.activeAgentId = data["activeAgentId"]
    if "name" in data or "title" in data:
        session.name = data.get("name") or data.get("title")
    if "systemPrompt" in data:
        session.systemPrompt = data["systemPrompt"]
    if "todos" in data:
        session.todos = [TodoItem(**t) for t in data["todos"]]

    session_manager.save_session(session)
    return {"session": session.model_dump()}


@router.delete("/api/harness/sessions")
async def delete_all_sessions(project_id: Optional[str] = None):
    count = session_manager.delete_all_sessions(project_id)
    return {"success": True, "deleted": count}


@router.delete("/api/harness/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_manager.delete_session(session_id)
    return {"success": deleted}


@router.get("/api/harness/plugins")
async def get_plugins():
    all_skills = skill_discovery.list_skills()
    qe_skills = [s["name"] for s in all_skills if "agentic-qe" in s.get("source", "").lower()]
    if not qe_skills:
        qe_skills = [s["name"] for s in all_skills if s["name"].startswith("qe-")]
    if "security-audit" not in qe_skills:
        qe_skills.append("security-audit")

    return {
        "plugins": [
            {
                "id": "agentic-qe",
                "name": "Agentic QE",
                "version": "1.6.0",
                "type": "plugin",
                "author": "Sarvesh Talele",
                "repository": "https://github.com/sarveshtalele/agentic-qe",
                "status": "loaded",
                "description": "Full test engineering lifecycle with 8 quality gates and guardrails",
                "skills": qe_skills,
                "agents": 8
            }
        ],
        "totalLocalSkills": len(all_skills)
    }


@router.get("/api/harness/skills")
async def get_skills():
    all_skills = skill_discovery.list_skills()
    return {
        "skills": all_skills,
        "total": len(all_skills)
    }


@router.get("/api/harness/evaluations")
async def get_evaluations():
    from backend.harness.agent_evals import global_agent_eval_engine
    return {"evaluations": global_agent_eval_engine.list_evaluations()}


@router.get("/api/harness/cache")
async def get_cache_stats():
    from backend.harness.cache import global_harness_cache
    return {"cache": global_harness_cache.stats()}


@router.post("/api/harness/documents")
async def create_harness_document(data: Dict[str, Any]):
    project_id = data.get("projectId") or "prj_agentic_qe"
    title = data.get("title") or "QE Test Engineering Documentation"
    kind = data.get("kind") or "prd"
    content = data.get("content") or "# QE Documentation\n\nGenerated by Agentic QE Harness."
    author = data.get("author") or "Agentic QE Harness"

    from backend.core import documents
    doc = documents.create(project_id=project_id, kind=kind, title=title, content=content, author=author)
    return {"document": doc}

@router.get("/api/harness/tools")
async def get_tools():
    qe_tools = build_qe_tools(workspace_dir)
    tools_list = [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
            "requiresApproval": t.requires_approval,
            "gateNumber": t.gate_number,
            "category": t.category
        }
        for t in qe_tools
    ]
    return {"tools": tools_list}


@router.get("/api/harness/mcp")
async def get_mcp():
    return {"servers": mcp_manager.list_servers()}


@router.post("/api/harness/mcp")
async def add_mcp(data: Dict[str, Any]):
    conf = MCPServerConfig(**data)
    mcp_manager.add_server(conf)
    return {"success": True, "server": conf.model_dump()}


@router.post("/api/harness/stop")
async def stop_execution(req: StopRequest):
    event = active_abort_events.get(req.sessionId)
    if event:
        event.set()
        return {"success": True, "stopped": True, "sessionId": req.sessionId}
    return {"success": True, "stopped": False, "message": "No active execution for session"}


@router.post("/api/harness/chat")
async def stream_chat(req: ChatRequest):
    session = None
    if req.sessionId:
        session = session_manager.get_session(req.sessionId)
    if not session:
        session = session_manager.create_session("Live QE Campaign", req.mode or "plan", project_id=req.projectId)

    if req.projectId:
        session.projectId = req.projectId
    if req.mode and req.mode != session.mode:
        session.mode = req.mode
    chosen_agent = req.agentId or req.activeAgentId
    if chosen_agent and chosen_agent != session.activeAgentId:
        session.activeAgentId = chosen_agent
    if req.systemPrompt:
        session.systemPrompt = req.systemPrompt

    # Centralized Platform LLM credentials from settings/environment
    central_cfg = platform_llm.current()
    llm_conf = LLMConfig(
        provider="openai",
        model=central_cfg.get("model") or "gpt-4o",
        api_key=central_cfg.get("api_key") or "",
        base_url=central_cfg.get("base_url") or "https://api.openai.com/v1"
    )

    abort_event = asyncio.Event()
    active_abort_events[session.id] = abort_event
    prompt_text = req.message or req.prompt or ""

    async def event_generator():
        try:
            async for sse_chunk in harness_agent.run(
                session=session,
                user_prompt=prompt_text,
                llm_config=llm_conf,
                abort_event=abort_event
            ):
                yield sse_chunk
            session_manager.save_session(session)
        finally:
            active_abort_events.pop(session.id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Project-scoped Harness Chat endpoint
@router.post("/api/projects/{project_id}/harness/chat")
async def project_stream_chat(project_id: str, req: ChatRequest):
    _project(project_id)
    req.projectId = project_id
    prompt_text = req.message or req.prompt or ""
    # Prepend project context binding if not already bound
    p = global_project_repo.get_project(project_id)
    if p:
        prefix = f"[Project Context: {p['name']} ({project_id})]\n"
        if not prompt_text.startswith(prefix) and not prompt_text.startswith("/"):
            prompt_text = f"{prefix}{prompt_text}"
    req.message = prompt_text
    req.prompt = prompt_text
    return await stream_chat(req)
