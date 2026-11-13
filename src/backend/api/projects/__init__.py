"""Projects API."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.projects import crud, export, members, overview
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions

router = APIRouter()
for _part in (crud, members, overview, export):
    router.include_router(_part.router)
