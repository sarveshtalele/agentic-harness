"""Trace explorer API: runs (root spans) and one run's span tree. Admins see all; anyone else only their own runs (core/tracing/queries.py)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from backend.core import auth
from backend.core.tracing import queries

router = APIRouter()


def _iso(value: str, name: str) -> str:
    """The stored form (UTC, milliseconds), so a time from the browser compares correctly with started_at."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, f"{name} must be an ISO date and time") from None
    return (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat(timespec="milliseconds")


@router.get("/api/traces")
def list_traces(project: str = "", user: str = "", agent: str = "", status: str = "", start: str = Query("", alias="from"), end: str = Query("", alias="to"),
                q: str = "", requests: bool = False, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return queries.list_runs(auth.current_user.get(), project=project, owner=user, agent=agent, status=status, start=_iso(start, "from"), end=_iso(end, "to"),
                             q=q[:200], requests=requests, limit=limit, offset=offset)


@router.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    return queries.get_trace(auth.current_user.get(), trace_id)
