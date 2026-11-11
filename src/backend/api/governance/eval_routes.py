"""Eval scores and cards, and the project metrics."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.common import _project
from backend.db import db, rows
from backend.maf import evals

router = APIRouter()

@router.get("/api/prompts/{agent}/scores")
def prompt_scores(agent: str):
    return evals.store.by_version(agent)


@router.get("/api/evals")
def list_evals():
    return evals.available()


@router.get("/api/evals/cards")
def eval_cards():
    """The four tiles of every agent card, plus whether RAGAS can run and which judge model is set."""
    ok, why = evals.ragas_evaluator.installed()
    return {"cards": evals.store.cards(), "ragas": {"installed": ok, "reason": why, "judge_model": evals.ragas_evaluator.judge_model()}, "benchmarks": evals.benchmarks()}


@router.get("/api/evals/{agent}")
def eval_history(agent: str):
    return evals.history(agent)


@router.get("/api/projects/{project_id}/metrics")
def metrics(project_id: str):
    """Numbers computed from stored runs and events. Empty until real work has happened."""
    _project(project_id)
    with db() as con:
        by_status = rows(con.execute("SELECT workflow, status, COUNT(*) AS count, SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out FROM runs WHERE project_id=? GROUP BY workflow, status", (project_id,)))
        durations = rows(con.execute("SELECT workflow, ROUND(AVG((julianday(ended_at)-julianday(started_at))*86400),1) AS avg_seconds, COUNT(*) AS count FROM runs WHERE project_id=? AND ended_at IS NOT NULL GROUP BY workflow", (project_id,)))
        tools_used = rows(con.execute("SELECT json_extract(e.data,'$.tool') AS tool, COUNT(*) AS calls, ROUND(AVG(json_extract(e.data,'$.ms'))) AS avg_ms FROM run_events e JOIN runs r ON r.id=e.run_id WHERE r.project_id=? AND e.type='tool' GROUP BY tool ORDER BY calls DESC", (project_id,)))
        agent_runs = rows(con.execute("SELECT agent, COUNT(*) AS calls, SUM(tokens_in+tokens_out) AS tokens, CAST(AVG(latency_ms) AS INT) AS avg_ms, SUM(status='error') AS errors FROM agent_calls WHERE project_id=? GROUP BY agent ORDER BY tokens DESC", (project_id,)))
    return {"runs": by_status, "durations": durations, "tools": tools_used, "agents": agent_runs}
