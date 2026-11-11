"""Bring code in from git, ZIP or a local folder."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from backend.config import project_dir, repo_dir
from backend.core import ledger
from backend.db import db, now
from backend.repos import git, github, scan
from backend.repos.ingest.base import IngestError, _rm_tree
from backend.repos.ingest.state import get
from backend.repos.ingest.zips import safe_extract


def _record(project_id: str, kind: str, url: str, ref: str, credential_id: str | None, actor: str) -> dict:
    repo = repo_dir(project_id)
    analysis = scan.analyze(repo)
    commit = git.head(repo)
    with db() as con:
        con.execute("INSERT OR REPLACE INTO repo_sources VALUES (?,?,?,?,?,?,?,?)", (project_id, kind, url, ref, credential_id, commit, json.dumps(analysis), now()))
    ledger.append(project_id, actor, "repo.ingested", url or "zip", {"kind": kind, "commit": commit, "files": analysis["total_files"]})
    return get(project_id)


def from_git(project_id: str, url: str, ref: str = "", credential_id: str | None = None, actor: str = "user") -> dict:
    if re.fullmatch(r"[\w.-]+/[\w.-]+", url.strip()):  # owner/repo shorthand
        url = f"https://github.com/{url.strip()}"
    token = github.token_for(credential_id)
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    staging = project_dir(project_id) / "repo.incoming"
    _rm_tree(staging)
    git.clone(url, staging, ref, token)  # the current repo survives a failed clone
    _rm_tree(repo_dir(project_id))
    staging.replace(repo_dir(project_id))
    return _record(project_id, "git", url, ref, credential_id, actor)


def from_zip(project_id: str, archive: Path, filename: str, actor: str = "user") -> dict:
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    staging = project_dir(project_id) / "repo.incoming"
    _rm_tree(staging)
    staging.mkdir(parents=True)
    safe_extract(archive, staging)
    entries = [p for p in staging.iterdir() if p.name != "__MACOSX"]
    root = entries[0] if len(entries) == 1 and entries[0].is_dir() else staging  # unwrap "project-main/" folders
    _rm_tree(repo_dir(project_id))
    root.replace(repo_dir(project_id))
    _rm_tree(staging)
    _rm_tree(repo_dir(project_id) / "__MACOSX")
    git.init_snapshot(repo_dir(project_id), f"Agentic QE Platform snapshot of {filename}")
    return _record(project_id, "zip", filename, "", None, actor)


def from_local(project_id: str, folder: str, actor: str = "user") -> dict:
    """Copy a local folder into the project. The original is never modified and symlinks are not followed."""
    source = Path(folder).expanduser()
    if not source.is_dir():
        raise IngestError(f"Not a folder: {folder}")
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    staging = project_dir(project_id) / "repo.incoming"
    _rm_tree(staging)
    shutil.copytree(source, staging, symlinks=True, ignore=lambda _d, names: [n for n in names if n in scan.SKIP_DIRS and n != ".git"] + [n for n in names if (Path(_d) / n).is_symlink()])
    _rm_tree(repo_dir(project_id))
    staging.replace(repo_dir(project_id))
    if git.is_repo(repo_dir(project_id)):
        return _record(project_id, "local", str(source), "", None, actor)
    git.init_snapshot(repo_dir(project_id), f"Agentic QE Platform snapshot of {source.name}")
    return _record(project_id, "local", str(source), "", None, actor)


def resync(project_id: str, actor: str = "user") -> dict:
    current = get(project_id)
    if not current:
        raise IngestError("No repository connected")
    if current["kind"] != "git":
        raise IngestError("Only Git sources can re-sync. Upload a new ZIP or import the folder again")
    return from_git(project_id, current["url"], current["ref"], current["credential_id"], actor)
