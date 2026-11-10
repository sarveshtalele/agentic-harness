"""Enterprise QE Harness API Router.
Exposes streaming SSE chat, persistent session management,
58 local machine skills discovery, and MCP tool server integration,
using the centralized platform credentials and project permissions.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.api.common import _project
from backend.core import auth
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


def _writable_project(project_id: str) -> None:
    """A body-supplied projectId is checked against the signed-in user. Someone else's project answers 404."""
    if not auth.can_see_project(project_id):
        raise HTTPException(404, "Not found")
    if not auth.can_write(project_id):
        raise HTTPException(403, "Your role does not allow changes in this project")


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
    project_id = data.get("projectId")
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    _writable_project(project_id)
    title = data.get("title") or "QE Test Engineering Documentation"
    kind = data.get("kind") or "prd"
    content = data.get("content") or "# QE Documentation\n\nGenerated by Agentic QE Harness."
    from backend.core import documents
    doc = documents.create(project_id=project_id, kind=kind, title=title, content=content, author=auth.signer())
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
    if req.projectId:
        _writable_project(req.projectId)
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


# Direct Document Upload & ChromaDB RAG Ingestion
@router.post("/api/harness/upload-document")
async def upload_harness_document(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    kind: str = Form("brd"),
    title: Optional[str] = Form(None)
):
    import time
    target_project = project_id
    if not target_project:
        raise HTTPException(status_code=400, detail="project_id is required")
    _writable_project(target_project)
    content_bytes = await file.read()
    filename = file.filename or "uploaded_document.txt"
    ext = os.path.splitext(filename)[1].lower()

    text = ""
    if ext in (".md", ".txt", ".json", ".yaml", ".yml"):
        text = content_bytes.decode("utf-8", errors="ignore")
    elif ext == ".docx":
        import io
        import xml.etree.ElementTree as ET
        import zipfile
        try:
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as docx:
                xml_content = docx.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                text = " ".join([node.text for node in tree.iter() if node.text])
        except Exception:
            text = content_bytes.decode("utf-8", errors="ignore")
    elif ext == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            text = content_bytes.decode("utf-8", errors="ignore")
    else:
        text = content_bytes.decode("utf-8", errors="ignore")

    doc_title = title or filename.replace(ext, "").replace("-", " ").replace("_", " ").title()

    from backend.db import db
    from backend.core import documents as docs_core
    # Store governed document through standard documents engine
    author = auth.signer()
    created = docs_core.create(
        project_id=target_project,
        kind=kind,
        title=doc_title,
        content=text,
        author=author,
        note=f"Uploaded via Autonomous QE Harness ({filename})"
    )
    doc_id = created["id"]

    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents WHERE project_id = ?", (target_project,))
        count = cur.fetchone()[0]
        clean_prefix = re.sub(r'[^a-zA-Z0-9]', '', target_project.replace('prj_', '')).upper()[:4] or "QE"
        gov_id = f"{clean_prefix}-DOC-{count:03d}"

    from backend.harness.rag_store import rag_store
    index_res = rag_store.index_document(
        project_id=target_project,
        doc_id=doc_id,
        title=doc_title,
        kind=kind,
        content=text
    )

    return {
        "success": True,
        "doc_id": doc_id,
        "governance_id": gov_id,
        "title": doc_title,
        "kind": kind,
        "filename": filename,
        "projectId": target_project,
        "chunksIndexed": index_res.get("indexed", 0),
        "vectorDb": "ChromaDB",
        "collection": index_res.get("collection", f"proj_{target_project}")
    }


class SkillTestRequest(BaseModel):
    skillName: str
    args: Optional[Dict[str, Any]] = None
    projectId: Optional[str] = None


@router.post("/api/harness/skills/test")
async def test_skill_endpoint(req: SkillTestRequest):
    from backend.harness.skill_tester import execute_and_test_skill
    workspace = os.getcwd()
    result = await execute_and_test_skill(
        skill_name=req.skillName,
        workspace_dir=workspace,
        test_args=req.args
    )
    return result


class RAGQueryRequest(BaseModel):
    query: str
    projectId: str
    topK: Optional[int] = 4


@router.post("/api/harness/rag-query")
async def rag_query_endpoint(req: RAGQueryRequest):
    from backend.harness.rag_store import rag_store
    hits = rag_store.query_context(req.query, req.projectId, top_k=req.topK or 4)
    grounding = rag_store.get_unified_grounding(req.projectId, query=req.query)
    return {
        "query": req.query,
        "projectId": req.projectId,
        "vectorHits": hits,
        "unifiedGrounding": grounding
    }

