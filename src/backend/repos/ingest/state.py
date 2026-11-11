"""Read and clear a project's connected repository record."""
from __future__ import annotations

import json
from backend.config import repo_dir
from backend.core import ledger
from backend.db import db, row
from backend.repos import git, scan
from backend.repos.ingest.analysis import _is_partial_analysis, normalize_analysis
from backend.repos.ingest.base import _rm_tree


def get(project_id: str) -> dict | None:
    try:
        with db() as con:
            found = row(con.execute("SELECT * FROM repo_sources WHERE project_id=?", (project_id,)))
    except Exception:
        return None
    if not found:
        return None

    raw_analysis = found.get("analysis")
    analysis = {}
    if isinstance(raw_analysis, str):
        try:
            analysis = json.loads(raw_analysis or "{}")
        except Exception:
            analysis = {}
    elif isinstance(raw_analysis, dict):
        analysis = raw_analysis

    repo = repo_dir(project_id)
    if repo.exists() and repo.is_dir():
        try:
            has_files = any(p.is_file() for p in repo.iterdir() if p.name != ".git") or any(scan.iter_files(repo))
        except Exception:
            has_files = False

        if has_files and _is_partial_analysis(analysis):
            try:
                fresh = scan.analyze(repo)
                if fresh:
                    analysis = fresh
                    commit = git.head(repo) or found.get("commit_sha", "")
                    with db() as con:
                        con.execute("UPDATE repo_sources SET analysis=?, commit_sha=? WHERE project_id=?", (json.dumps(analysis), commit, project_id))
                    found["commit_sha"] = commit
            except Exception:
                pass

    found["analysis"] = normalize_analysis(analysis, repo)
    try:
        found["log"] = git.log(repo) if repo.exists() and git.is_repo(repo) else []
    except Exception:
        found["log"] = []
    return found


def disconnect(project_id: str, actor: str = "user") -> None:
    with db() as con:
        con.execute("DELETE FROM repo_sources WHERE project_id=?", (project_id,))
    _rm_tree(repo_dir(project_id))
    ledger.append(project_id, actor, "repo.disconnected")
