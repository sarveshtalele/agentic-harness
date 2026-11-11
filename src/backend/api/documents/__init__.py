"""Documents API."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.documents import ai, crud, exports, templates, upload, versions
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions

router = APIRouter()
for _part in (crud, versions, exports, ai, upload, templates):
    router.include_router(_part.router)
