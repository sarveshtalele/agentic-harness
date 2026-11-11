"""Projects API: the project overview."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.common import _project
from backend.api.projects.crud import get_project
from backend.core import documents, gates
from backend.db import db, rows
from backend.repos import ingest

router = APIRouter()


@router.get("/api/projects/{project_id}/overview")
def overview(project_id: str):
    _project(project_id)
    with db() as con:
        pending = rows(con.execute("SELECT id, run_id, gate, title, summary, created_at FROM approvals WHERE project_id=? AND status='pending' ORDER BY created_at", (project_id,)))
        latest = rows(con.execute("SELECT id, workflow, status, started_at, ended_at, error FROM runs WHERE project_id=? ORDER BY started_at DESC LIMIT 6", (project_id,)))
    repo = ingest.get(project_id)
    repo_data = None
    if repo:
        analysis_data = repo.get("analysis") or {}
        repo_data = {
            "kind": repo.get("kind"),
            "url": repo.get("url"),
            "commit_sha": repo.get("commit_sha"),
            "scanned_at": repo.get("scanned_at"),
            "analysis": {k: analysis_data.get(k) for k in ("mode", "languages", "frameworks", "test_runners", "total_files", "test_file_count")},
        }
    return {"project": get_project(project_id), "gates": gates.status(project_id), "pending_approvals": pending, "recent_runs": latest,
            "documents": documents.list_for(project_id)[:8], "repo": repo_data}
