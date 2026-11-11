"""Agent overview, settings, guardrail events, and eval runs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core import auth
from backend.maf import evals, governance

router = APIRouter()

class AgentSettingsIn(BaseModel):
    enabled: bool
    max_tokens: int | None = None
    reason: str = ""
    model: str = ""


@router.get("/api/agents")
def list_agents():
    return governance.overview()


@router.get("/api/agents/guardrail-events")
def guardrail_events():
    return governance.recent_events()


@router.post("/api/agents/evals/run-all")
async def run_all_evals():
    return await evals.run_all()


@router.get("/api/agents/{agent}")
def agent_detail(agent: str):
    item = next((a for a in governance.overview() if a["key"] == agent), None)
    if not item:
        raise HTTPException(404, f"Agent not found: {agent}")
    item = {**item, "settings_by_name": auth.display_names({item["settings_by"]}).get(item["settings_by"], item["settings_by"]) if item.get("settings_by") else None}
    admin = auth.current_user.get()["role"] == "admin"  # recent calls and events span projects
    return {**item, "calls_recent": governance.recent_calls(agent) if admin else [], "events_recent": governance.recent_events(agent) if admin else [], "evals": evals.history(agent), "has_evals": agent in evals.available()}


@router.put("/api/agents/{agent}/settings")
def agent_settings(agent: str, body: AgentSettingsIn):
    try:
        governance.update_settings(agent, body.enabled, body.max_tokens, auth.signer(), body.reason, body.model)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return agent_detail(agent)


class EvalRunIn(BaseModel):
    benchmark: str = ""
    repeats: int = Field(1, ge=1, le=5)
    ragas: bool = True  # model-graded RAGAS & Specter metrics enabled by default


@router.post("/api/agents/{agent}/evals")
async def run_agent_eval(agent: str, body: EvalRunIn | None = None):
    body = body or EvalRunIn()
    try:
        return await evals.run(agent, benchmark=body.benchmark, repeats=body.repeats, ragas=body.ragas)
    except KeyError as exc:
        raise HTTPException(404, str(exc.args[0])) from exc


@router.get("/api/agents/{agent}/metrics")
def agent_metrics(agent: str):
    """Every metric with its caveats, the trend by prompt version, the spread over repeated runs, and the latest cases, worst first."""
    if agent not in governance.POLICIES:
        raise HTTPException(404, f"No agent {agent}")
    return {**evals.store.detail(agent), "cases": evals.cases_worst_first(agent)}
