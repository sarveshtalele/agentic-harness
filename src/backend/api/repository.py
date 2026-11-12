"""Repository API."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import (
    PlainTextResponse,
    Response,
)
from pydantic import BaseModel, Field

from backend.api.common import _project, _save_upload
from backend.config import project_dir, repo_dir, sandbox_dir
from backend.core import cli_workspaces
from backend.core import auth
from backend.core.security import safe_path
from backend.maf import agui, engine, evals, governance, llm, workflows  # noqa: F401 - workflows registers definitions
from backend.repos import ingest, scan, sandbox

router = APIRouter()


class GitIn(BaseModel):
    url: str
    ref: str = ""
    credential_id: str | None = None


@router.get("/api/projects/{project_id}/repo")
def get_repo(project_id: str):
    _project(project_id)
    try:
        repo = ingest.get(project_id)
    except (FileNotFoundError, KeyError):
        return None
    except Exception:
        return None
    if not repo:
        return None
    try:
        sbox_info = sandbox.info(project_id)
    except Exception:
        sbox_info = None
    return {**repo, "sandbox": sbox_info}


@router.post("/api/projects/{project_id}/repo/git")
async def connect_git(project_id: str, body: GitIn):
    _project(project_id)
    try:
        return await asyncio.to_thread(ingest.from_git, project_id, body.url, body.ref, body.credential_id, auth.signer())
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/projects/{project_id}/repo/zip")
async def upload_zip(project_id: str, file: UploadFile = File(...)):
    _project(project_id)
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=project_dir(project_id)) as tmp:
        archive = Path(tmp) / "upload.zip"
        await _save_upload(file, archive)
        try:
            return await asyncio.to_thread(ingest.from_zip, project_id, archive, file.filename or "upload.zip", auth.signer())
        except (FileNotFoundError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))


class LocalIn(BaseModel):
    path: str = Field(min_length=1)


@router.post("/api/projects/{project_id}/repo/local")
async def import_local(project_id: str, body: LocalIn):
    _project(project_id)
    try:
        return await asyncio.to_thread(ingest.from_local, project_id, body.path, auth.signer())
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/projects/{project_id}/workspace")
async def bind_workspace(project_id: str, body: LocalIn):
    """aqh CLI only: work directly in a folder on this machine (core/cli_workspaces.py)."""
    _project(project_id)
    try:
        return {"project_id": project_id, "path": str(cli_workspaces.bind(project_id, body.path))}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/projects/{project_id}/repo/resync")
async def resync(project_id: str):
    _project(project_id)
    try:
        return await asyncio.to_thread(ingest.resync, project_id, auth.signer())
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/api/projects/{project_id}/repo", status_code=204)
def disconnect(project_id: str):
    _project(project_id)
    try:
        ingest.disconnect(project_id, auth.signer())
    except (FileNotFoundError, KeyError):
        pass
    return Response(status_code=204)


@router.get("/api/projects/{project_id}/repo/tree")
def repo_tree(project_id: str):
    _project(project_id)
    root = repo_dir(project_id)
    files = []
    if root.exists():
        files = scan.tree(root)
    if not files:
        sbox = sandbox_dir(project_id)
        if sbox.exists():
            files = scan.tree(sbox)
    return {"files": files or []}


@router.get("/api/projects/{project_id}/repo/file", response_class=PlainTextResponse)
def repo_file(project_id: str, path: str):
    _project(project_id)
    root = repo_dir(project_id)
    if not root.exists():
        sbox = sandbox_dir(project_id)
        if sbox.exists():
            root = sbox
    try:
        target = safe_path(root, path)
    except (ValueError, KeyError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not target.is_file():
        # Fallback to sandbox if root was repo_dir
        try:
            sbox_target = safe_path(sandbox_dir(project_id), path)
            if sbox_target.is_file():
                target = sbox_target
        except Exception:
            pass

    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        content = scan._read(target)
        return content if content else "(binary, empty, or too large to display)"
    except (FileNotFoundError, KeyError, OSError):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
