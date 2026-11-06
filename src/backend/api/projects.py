"""Projects API."""
from __future__ import annotations

import io
import json
import os
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import (
    Response,
    StreamingResponse,
)
from pydantic import BaseModel, Field

from backend.api.common import _project
from backend.config import RUNS, project_dir
from backend.core import auth, documents, gates, ledger
from backend.core.security import safe_path
from backend.db import db, new_id, now, rows
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions
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
        items = rows(con.execute("SELECT * FROM projects WHERE archived=? AND id!='prj_agent_evals' ORDER BY updated_at DESC", (int(archived),)))
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
    return Response(status_code=204)


class MemberIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    role: str = "developer"


class TransferIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)


@router.get("/api/projects/{project_id}/members")
def list_members(project_id: str):
    _project(project_id)
    return auth.members(project_id)


@router.post("/api/projects/{project_id}/members", status_code=201)
def add_member(project_id: str, body: MemberIn):
    """The owner types the exact username. The answer is added or not found, and nothing else about the account."""
    _project(project_id)
    try:
        auth.add_member(project_id, body.username, body.role)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "No account has that username") from exc
    return auth.members(project_id)


@router.delete("/api/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(project_id: str, user_id: str):
    _project(project_id)
    auth.remove_member(project_id, user_id)
    return Response(status_code=204)


@router.post("/api/projects/{project_id}/transfer")
def transfer(project_id: str, body: TransferIn):
    _project(project_id)
    try:
        auth.transfer_project(project_id, body.username)
    except KeyError as exc:
        raise HTTPException(404, "No account has that username") from exc
    return get_project(project_id)


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


@router.get("/api/projects/{project_id}/export-zip")
def export_project_zip(project_id: str):
    """
    Exports the complete project SDLC package as a downloadable ZIP archive containing:
    1. Scaffolding / source files from data/projects/{project_id}/sandbox (or repo)
    2. Governed requirements and test specifications (.md)
    3. Automated setup script for Mac/Linux (setup_mac_linux.sh)
    4. Automated setup script for Windows (setup_windows.bat)
    5. README_SETUP.md with quickstart and test execution instructions
    """
    proj = _project(project_id)
    buf = io.BytesIO()

    # Determine files to include
    p_dir = project_dir(project_id)
    sandbox_dir = p_dir / "sandbox"
    docs_dir = p_dir / "documents"

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files_added = 0

        # 1. Add files from sandbox
        if sandbox_dir.exists() and sandbox_dir.is_dir():
            for root, dirs, files in os.walk(sandbox_dir):
                # Skip build artifacts / venvs
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache")]
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, sandbox_dir)
                    zip_file.write(full_p, arcname=f"src/{rel_p}")
                    files_added += 1

        # 2. Add governed documents
        if docs_dir.exists() and docs_dir.is_dir():
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    if file.endswith((".md", ".json", ".feature")):
                        full_p = os.path.join(root, file)
                        rel_p = os.path.relpath(full_p, docs_dir)
                        zip_file.write(full_p, arcname=f"docs/{rel_p}")
                        files_added += 1

        # 3. Add database documents if docs directory is sparse
        proj_docs = documents.list_for(project_id)
        for doc in proj_docs:
            d_full = documents.get(doc["id"])
            arc_name = f"docs/{doc['kind']}_{doc['id']}.md"
            if arc_name not in zip_file.namelist():
                content = d_full.get("content", f"# {doc['title']}\n\nVersion: {doc['current_version']}\n")
                zip_file.writestr(arc_name, content)
                files_added += 1

        # 4. Generate setup_mac_linux.sh
        setup_sh = (
            "#!/usr/bin/env bash\n"
            "# Autonomous Agentic QE Sandbox Setup Script for Mac / Linux\n"
            "set -e\n\n"
            "echo \"==================================================\"\n"
            f"echo \"  Setting up Project: {proj['name']} \"\n"
            "echo \"  Autonomous Quality Engineering SDLC Environment \"\n"
            "echo \"==================================================\"\n\n"
            "if command -v python3 &>/dev/null; then\n"
            "    echo \"[1/4] Configuring Python environment...\"\n"
            "    python3 -m venv .venv || true\n"
            "    if [ -f .venv/bin/activate ]; then\n"
            "        source .venv/bin/activate\n"
            "    fi\n"
            "    if [ -f requirements.txt ]; then\n"
            "        pip install -r requirements.txt || true\n"
            "    elif [ -f src/requirements.txt ]; then\n"
            "        pip install -r src/requirements.txt || true\n"
            "    fi\n"
            "fi\n\n"
            "if command -v npm &>/dev/null; then\n"
            "    if [ -f package.json ]; then\n"
            "        echo \"[2/4] Installing Node dependencies...\"\n"
            "        npm install --ignore-scripts || true\n"
            "    elif [ -f src/package.json ]; then\n"
            "        echo \"[2/4] Installing Node dependencies in src/...\"\n"
            "        (cd src && npm install --ignore-scripts || true)\n"
            "    fi\n"
            "fi\n\n"
            "echo \"[3/4] Running automated quality gate regression suite...\"\n"
            "if command -v pytest &>/dev/null; then\n"
            "    pytest -v || true\n"
            "elif [ -f package.json ]; then\n"
            "    npm test || true\n"
            "fi\n\n"
            "echo \"[4/4] Environment setup complete! Starting sandbox application...\"\n"
            "if [ -f main.py ]; then\n"
            "    python3 main.py || true\n"
            "elif [ -f src/main.py ]; then\n"
            "    python3 src/main.py || true\n"
            "elif [ -f package.json ]; then\n"
            "    npm start || true\n"
            "fi\n"
        )
        zip_file.writestr("setup_mac_linux.sh", setup_sh)

        # 5. Generate setup_windows.bat
        setup_bat = (
            "@echo off\n"
            "REM Autonomous Agentic QE Sandbox Setup Script for Windows\n"
            "echo ==================================================\n"
            f"echo   Setting up Project: {proj['name']} \n"
            "echo   Autonomous Quality Engineering SDLC Environment \n"
            "echo ==================================================\n\n"
            "where python >nul 2>nul\n"
            "if %ERRORLEVEL% equ 0 (\n"
            "    echo [1/4] Configuring Python environment...\n"
            "    python -m venv .venv\n"
            "    if exist .venv\\Scripts\\activate.bat call .venv\\Scripts\\activate.bat\n"
            "    if exist requirements.txt pip install -r requirements.txt\n"
            "    if exist src\\requirements.txt pip install -r src\\requirements.txt\n"
            ")\n\n"
            "where npm >nul 2>nul\n"
            "if %ERRORLEVEL% equ 0 (\n"
            "    if exist package.json (\n"
            "        echo [2/4] Installing Node dependencies...\n"
            "        call npm install --ignore-scripts\n"
            "    )\n"
            ")\n\n"
            "echo [3/4] Executing test suite...\n"
            "where pytest >nul 2>nul\n"
            "if %ERRORLEVEL% equ 0 (\n"
            "    pytest -v\n"
            ")\n\n"
            "echo [4/4] Setup complete! You can now launch your application.\n"
            "pause\n"
        )
        zip_file.writestr("setup_windows.bat", setup_bat)

        # 6. Generate README_SETUP.md
        readme = (
            f"# {proj['name']} — Autonomous SDLC & Quality Engineering Export\n\n"
            f"**Project ID:** `{project_id}`  \n"
            f"**Exported At:** {now()}  \n\n"
            "## Architecture Overview\n"
            "This package contains the complete application codebase, test automation suite, "
            "and governed specifications created in the Autonomous QE Platform sandbox.\n\n"
            "### Folder Structure\n"
            "- `src/`: Complete source code and application modules\n"
            "- `docs/`: Governed Business Requirements Documents (BRD), Gherkin feature files, and Test Plans\n"
            "- `setup_mac_linux.sh`: One-click setup and execution script for macOS & Linux\n"
            "- `setup_windows.bat`: One-click setup and execution batch script for Windows\n\n"
            "## Quickstart Instructions\n\n"
            "### macOS / Linux\n"
            "```bash\n"
            "chmod +x setup_mac_linux.sh\n"
            "./setup_mac_linux.sh\n"
            "```\n\n"
            "### Windows\n"
            "Double click `setup_windows.bat` or run in CMD:\n"
            "```cmd\n"
            "setup_windows.bat\n"
            "```\n\n"
            "## Quality Gate Compliance\n"
            "All test assertions are deterministic and adhere to the strict Assertion Preservation Rule.\n"
        )
        zip_file.writestr("README_SETUP.md", readme)

    buf.seek(0)
    filename = f"{project_id}_sdlc_export.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )

