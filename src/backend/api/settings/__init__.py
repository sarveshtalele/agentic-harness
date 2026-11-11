"""Connections and settings API."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.settings import connections, model_list, preferences, usage_report
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions

router = APIRouter()
for _part in (connections, model_list, preferences, usage_report):
    router.include_router(_part.router)
