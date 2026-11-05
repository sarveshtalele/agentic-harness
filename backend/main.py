import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from maf.core.session import AgentSessionManager, SessionState
from maf.core.harness_agent import HarnessAgent
from maf.skills.discovery import LocalSkillDiscovery
from maf.llm.config import load_llm_config, save_llm_config, LLMConfig
from maf.llm.client import LLMClient
from maf.tools.approval_manager import global_approval_manager
from maf.tools.mcp_manager import MCPClientManager, MCPServerConfig
from qe.agents import list_all_agents
from qe.tools import build_qe_tools

app = FastAPI(
    title="Agentic QE Harness Backend",
    description="Python FastAPI backend powered by Microsoft Agent Framework (MAF 2.0)",
    version="2.0.0"
)

# SEC-01 Remediated: Explicitly restrict CORS to trusted local origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

session_manager = AgentSessionManager()
mcp_manager = MCPClientManager()
workspace_dir = os.path.dirname(os.path.dirname(__file__))
skill_discovery = LocalSkillDiscovery(workspace_dir)
harness_agent = HarnessAgent(workspace_dir, skill_discovery=skill_discovery)

# Active abort events per session for the Stop Execution feature
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

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "engine": "Microsoft Agent Framework (MAF 2.0) Python Backend"}

@app.get("/api/config")
async def get_config():
    config = load_llm_config()
    client = LLMClient(config)
    data = config.model_dump()
    is_conf = client.is_configured()
    data["configured"] = is_conf
    data["is_configured"] = is_conf
    data["has_api_key"] = bool(config.api_key.strip() if config.api_key else False)
    return data

@app.post("/api/config")
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

@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": session_manager.list_sessions()}

@app.post("/api/sessions")
async def create_session(data: Dict[str, Any] = {}):
    name = data.get("name")
    mode = data.get("mode", "plan")
    session = session_manager.create_session(name, mode)
    return {"session": session.model_dump()}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}

@app.patch("/api/sessions/{session_id}")
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
        from maf.core.session import TodoItem
        session.todos = [TodoItem(**t) for t in data["todos"]]

    session_manager.save_session(session)
    return {"session": session.model_dump()}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_manager.delete_session(session_id)
    return {"success": deleted}

@app.get("/api/agents")
async def get_agents():
    return {"agents": list_all_agents()}

# Distinct First-Party Plugins endpoint
@app.get("/api/plugins")
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

# Local Machine Skills Catalog Endpoint (All 58 Skills)
@app.get("/api/skills")
async def get_skills():
    skills = skill_discovery.list_skills()
    return {
        "skills": skills,
        "total": len(skills)
    }

@app.get("/api/skills/{skill_name}")
async def get_skill(skill_name: str):
    sk = skill_discovery.get_skill(skill_name)
    if not sk:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found on local machine.")
    return {"skill": sk.model_dump()}

@app.get("/api/tools")
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

# Distinct Third-Party MCP Servers endpoint
@app.get("/api/mcp")
async def get_mcp():
    return {"servers": mcp_manager.list_servers()}

@app.post("/api/mcp")
async def add_mcp(data: Dict[str, Any]):
    conf = MCPServerConfig(**data)
    mcp_manager.add_server(conf)
    return {"success": True, "server": conf.model_dump()}

@app.post("/api/stop")
async def stop_execution(req: StopRequest):
    event = active_abort_events.get(req.sessionId)
    if event:
        event.set()
        return {"success": True, "stopped": True, "sessionId": req.sessionId}
    return {"success": True, "stopped": False, "message": "No active execution for session"}

@app.get("/api/approvals")
async def get_approvals():
    return {"pending": global_approval_manager.get_pending_list()}

@app.post("/api/approvals")
async def resolve_approval(req: ApprovalDecisionRequest):
    resolved = global_approval_manager.resolve_approval(
        req.approvalId,
        req.action,
        req.feedback
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Approval request not found or resolved")
    return {"success": True, "approvalId": req.approvalId, "action": req.action}

@app.post("/api/chat")
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

    abort_event = asyncio.Event()
    active_abort_events[session.id] = abort_event

    llm_config = load_llm_config()
    if session.systemPrompt:
        llm_config.system_prompt = session.systemPrompt

    async def event_generator():
        try:
            async for chunk in harness_agent.run(
                session=session,
                user_prompt=req.message,
                llm_config=llm_config,
                abort_event=abort_event
            ):
                yield chunk
            session_manager.save_session(session)
        except Exception as e:
            err_json = json.dumps({"type": "TEXT_CHUNK", "chunk": f"\n\n❌ **Harness Error:** {str(e)}\n"})
            yield f"data: {err_json}\n\n"
        finally:
            if session.id in active_abort_events:
                del active_abort_events[session.id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/copilotkit")
async def copilotkit_endpoint(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    last_msg = messages[-1].get("content", "") if messages else ""

    session = session_manager.create_session("CopilotKit Session", "plan")
    llm_config = load_llm_config()

    async def sse_gen():
        async for chunk in harness_agent.run(session, last_msg, llm_config):
            yield chunk

    return StreamingResponse(sse_gen(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
