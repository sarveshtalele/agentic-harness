"""MAF 2.0 Harness API Router.
Exposes streaming SSE chat, persistent session management,
58 local machine skills discovery, MCP tool server integration,
and human-in-the-loop gate approvals.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.config import ROOT
from backend.harness.approval_manager import global_approval_manager
from backend.harness.discovery import LocalSkillDiscovery
from backend.harness.harness_agent import HarnessAgent
from backend.harness.llm_client import LLMClient
from backend.harness.llm_config import LLMConfig, load_llm_config, save_llm_config
from backend.harness.mcp_manager import MCPClientManager, MCPServerConfig
from backend.harness.project_repository import global_project_repo
from backend.harness.qe_agents import list_all_agents
from backend.harness.qe_tools import build_qe_tools
from backend.harness.session import AgentSessionManager, SessionState, TodoItem

router = APIRouter(tags=["harness"])

workspace_dir = str(ROOT)
session_manager = AgentSessionManager()
mcp_manager = MCPClientManager()
skill_discovery = LocalSkillDiscovery(workspace_dir)
harness_agent = HarnessAgent(workspace_dir, skill_discovery=skill_discovery)

active_abort_events: Dict[str, asyncio.Event] = {}


class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: str
    mode: Optional[str] = "plan"
    agentId: Optional[str] = None
    systemPrompt: Optional[str] = None


class StopRequest(BaseModel):
    sessionId: str


class ApprovalDecisionRequest(BaseModel):
    approvalId: str
    action: str
    feedback: Optional[str] = None


@router.get("/api/config")
async def get_config():
    config = load_llm_config()
    client = LLMClient(config)
    data = config.model_dump()
    is_conf = client.is_configured()
    data["configured"] = is_conf
    data["is_configured"] = is_conf
    data["has_api_key"] = bool(config.api_key.strip() if config.api_key else False)
    return data


@router.post("/api/config")
async def update_config(config_data: Dict[str, Any]):
    config = LLMConfig(**config_data)
    save_llm_config(config)
    client = LLMClient(config)
    data = config.model_dump()
    is_conf = client.is_configured()
    data["configured"] = is_conf
    data["is_configured"] = is_conf
    data["has_api_key"] = bool(config.api_key.strip() if config.api_key else False)
    return {"status": "success", "config": data}


@router.get("/api/sessions")
async def list_sessions():
    return {"sessions": session_manager.list_sessions()}


@router.post("/api/sessions")
async def create_session(data: Dict[str, Any] = {}):
    name = data.get("name")
    mode = data.get("mode", "plan")
    session = session_manager.create_session(name, mode)
    return {"session": session.model_dump()}


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, data: Dict[str, Any]):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if "mode" in data:
        session.mode = data["mode"]
    if "activeAgentId" in data:
        session.activeAgentId = data["activeAgentId"]
    if "name" in data:
        session.name = data["name"]
    if "systemPrompt" in data:
        session.systemPrompt = data["systemPrompt"]
    if "todos" in data:
        session.todos = [TodoItem(**t) for t in data["todos"]]

    session_manager.save_session(session)
    return {"session": session.model_dump()}


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_manager.delete_session(session_id)
    return {"success": deleted}


@router.get("/api/agents")
async def get_agents():
    return {"agents": list_all_agents()}


@router.get("/api/plugins")
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


@router.get("/api/skills")
async def get_skills():
    skills = skill_discovery.list_skills()
    return {
        "skills": skills,
        "total": len(skills)
    }


@router.get("/api/skills/{skill_name}")
async def get_skill(skill_name: str):
    sk = skill_discovery.get_skill(skill_name)
    if not sk:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found on local machine.")
    return {"skill": sk.model_dump()}


@router.get("/api/tools")
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


@router.get("/api/mcp")
async def get_mcp():
    return {"servers": mcp_manager.list_servers()}


@router.post("/api/mcp")
async def add_mcp(data: Dict[str, Any]):
    conf = MCPServerConfig(**data)
    mcp_manager.add_server(conf)
    return {"success": True, "server": conf.model_dump()}


@router.post("/api/stop")
async def stop_execution(req: StopRequest):
    event = active_abort_events.get(req.sessionId)
    if event:
        event.set()
        return {"success": True, "stopped": True, "sessionId": req.sessionId}
    return {"success": True, "stopped": False, "message": "No active execution for session"}


@router.get("/api/approvals")
async def get_approvals():
    return {"pending": global_approval_manager.get_pending_list()}


@router.post("/api/approvals")
async def resolve_approval(req: ApprovalDecisionRequest):
    resolved = global_approval_manager.resolve_approval(
        req.approvalId,
        req.action,
        req.feedback
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Approval request not found or resolved")
    return {"success": True, "approvalId": req.approvalId, "action": req.action}


@router.post("/api/chat")
async def stream_chat(req: ChatRequest):
    session = None
    if req.sessionId:
        session = session_manager.get_session(req.sessionId)
    if not session:
        session = session_manager.create_session("Live QE Campaign", req.mode or "plan")

    if req.mode and req.mode != session.mode:
        session.mode = req.mode
    if req.agentId and req.agentId != session.activeAgentId:
        session.activeAgentId = req.agentId
    if req.systemPrompt:
        session.systemPrompt = req.systemPrompt

    llm_conf = load_llm_config()
    abort_event = asyncio.Event()
    active_abort_events[session.id] = abort_event

    async def event_generator():
        try:
            async for sse_chunk in harness_agent.run(
                session=session,
                user_prompt=req.message,
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
