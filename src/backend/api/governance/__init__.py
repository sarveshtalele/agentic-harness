"""Governance API."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.governance import agent_routes, decisions, eval_routes, prompt_routes
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions

router = APIRouter()
for _part in (decisions, prompt_routes, agent_routes, eval_routes):
    router.include_router(_part.router)
