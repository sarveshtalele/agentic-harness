"""Projects API: list, create, read, update, archive and delete."""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.config import RUNS, project_dir
from backend.core import auth, ledger
from backend.core.security import safe_path
from backend.db import db, new_id, now, rows
from backend.maf import harness
from backend.repos import ingest

router = APIRouter()


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    archived: bool | None = None


def _project_summary(item: dict) -> dict:
    with db() as con:
        counts = con.execute(
            """SELECT (SELECT COUNT(*) FROM documents WHERE project_id=:p) AS documents,
                      (SELECT COUNT(*) FROM runs WHERE project_id=:p) AS runs,
                      (SELECT COUNT(*) FROM findings WHERE project_id=:p AND status IN ('open','fix_attempted')) AS findings,
                      (SELECT COUNT(*) FROM approvals WHERE project_id=:p AND status='pending') AS pending,
                      (SELECT COUNT(*) FROM gates WHERE project_id=:p AND status='approved') AS gates_approved""",
            {"p": item["id"]},
        ).fetchone()
        repo = con.execute("SELECT kind, url, commit_sha, analysis FROM repo_sources WHERE project_id=?", (item["id"],)).fetchone()
    analysis = {}
    if repo and repo["analysis"]:
        try:
            analysis = json.loads(repo["analysis"])
        except Exception:
            analysis = {}
    mine = auth.project_role(item["id"])
    can_sign = [g for g in range(6) if not auth.gate_signing_problem(item["id"], g)]
    repo_info = None
    if repo:
        commit_sha = (repo["commit_sha"] or "")[:10]
        langs = analysis.get("languages") or []
        repo_info = {
            "kind": repo["kind"],
            "url": repo["url"],
            "commit": commit_sha,
            "languages": list(langs)[:4] if isinstance(langs, (list, dict, tuple)) else [],
        }
    return {**item, "my_role": mine, "can_write": auth.can_write(item["id"]), "can_sign": can_sign, **dict(counts), "archived": bool(item["archived"]),
            "repo": repo_info}


@router.get("/api/projects")
def list_projects(archived: bool = False):
    with db() as con:
        items = rows(con.execute("SELECT * FROM projects WHERE archived=? AND id NOT IN ('prj_agent_evals', 'prj_platform') ORDER BY updated_at DESC", (int(archived),)))
    return [_project_summary(i) for i in items if auth.can_see_project(i["id"])]


@router.post("/api/projects", status_code=201)
def create_project(body: ProjectIn):
    item = {"id": new_id("prj"), "name": body.name.strip(), "description": body.description.strip(), "owner_id": auth.current_user.get()["id"], "created_at": now(), "updated_at": now()}
    with db() as con:
        con.execute("INSERT INTO projects (id, name, description, owner_id, created_at, updated_at) VALUES (:id,:name,:description,:owner_id,:created_at,:updated_at)", item)
    ledger.append(item["id"], auth.signer(), "project.created", item["id"], {"name": item["name"]})
    return _project_summary(_project(item["id"]))


@router.get("/api/projects/{project_id}")
def get_project(project_id: str):
    return _project_summary(_project(project_id))


@router.patch("/api/projects/{project_id}")
def patch_project(project_id: str, body: ProjectPatch):
    current = _project(project_id)
    with db() as con:
        con.execute("UPDATE projects SET name=?, description=?, archived=?, updated_at=? WHERE id=?",
                    (body.name or current["name"], current["description"] if body.description is None else body.description,
                     current["archived"] if body.archived is None else int(body.archived), now(), project_id))
    return get_project(project_id)


@router.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    _project(project_id)
    with db() as con:
        run_ids = [r["id"] for r in con.execute("SELECT id FROM runs WHERE project_id=?", (project_id,))]
        con.execute("DELETE FROM projects WHERE id=?", (project_id,))
    for run_id in filter(None, run_ids):  # saved failure replies and finished batches belong to the project's runs
        ingest._rm_tree(safe_path(RUNS, run_id, for_write=True))
    ingest._rm_tree(project_dir(project_id))
    ingest._rm_tree(safe_path(harness.HARNESS_DIR, project_id, for_write=True))  # the harness's memory, todos and history for this project
    return Response(status_code=204)
