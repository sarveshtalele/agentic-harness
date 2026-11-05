"""Harness Project Knowledge Repository & Data Access Object (DAO).
Implements Pattern 3.01 (Repository) and Pattern 3.02 (DAO) from Ashish Patel's
Agent Harness Engineering Patterns, connecting the MAF 2.0 Harness directly to
the SQLite Write-Ahead Log (WAL) database (atlas.sqlite3).
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from backend.db import db, rows, row, new_id, now


class ProjectRepository:
    """Provides strongly-typed, grounded query access to project knowledge."""

    def list_projects(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        with db() as con:
            sql = """
                SELECT 
                    p.id, p.name, p.description, p.created_at, p.updated_at, p.archived,
                    (SELECT COUNT(*) FROM documents d WHERE d.project_id = p.id) AS documents,
                    (SELECT COUNT(*) FROM findings f WHERE f.project_id = p.id AND f.status != 'closed') AS findings,
                    (SELECT COUNT(*) FROM runs r WHERE r.project_id = p.id) AS runs,
                    (SELECT COUNT(*) FROM approvals a WHERE a.project_id = p.id AND a.status = 'pending') AS pending,
                    (SELECT COUNT(*) FROM gates g WHERE g.project_id = p.id AND g.status = 'approved') AS gates_approved
                FROM projects p
            """
            if not include_archived:
                sql += " WHERE p.archived = 0"
            sql += " ORDER BY p.updated_at DESC"
            
            res = rows(con.execute(sql))
            # Enrich with repo sources
            for item in res:
                repo_row = row(con.execute("SELECT url, kind, ref, commit_sha, analysis FROM repo_sources WHERE project_id = ?", (item["id"],)))
                if repo_row:
                    try:
                        analysis = json.loads(repo_row.get("analysis") or "{}")
                    except Exception:
                        analysis = {}
                    item["repo"] = {
                        "url": repo_row.get("url"),
                        "kind": repo_row.get("kind"),
                        "ref": repo_row.get("ref"),
                        "commit": repo_row.get("commit_sha"),
                        "languages": analysis.get("languages", ["TypeScript", "Python"]),
                        "frameworks": analysis.get("frameworks", ["Next.js", "FastAPI"])
                    }
                else:
                    item["repo"] = None
            return res

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with db() as con:
            p = row(con.execute("SELECT * FROM projects WHERE id = ?", (project_id,)))
            if not p:
                return None
            
            repo = row(con.execute("SELECT * FROM repo_sources WHERE project_id = ?", (project_id,)))
            docs = rows(con.execute("SELECT id, title, kind, status, current_version, updated_at FROM documents WHERE project_id = ? ORDER BY updated_at DESC", (project_id,)))
            findings_list = rows(con.execute("SELECT * FROM findings WHERE project_id = ? ORDER BY created_at DESC", (project_id,)))
            gates_list = rows(con.execute("SELECT * FROM gates WHERE project_id = ? ORDER BY gate ASC", (project_id,)))
            recent_runs = rows(con.execute("SELECT id, workflow, status, error, tokens_in, tokens_out, started_at, ended_at FROM runs WHERE project_id = ? ORDER BY started_at DESC LIMIT 5", (project_id,)))
            mems = rows(con.execute("SELECT id, content, created_at FROM memories WHERE project_id = ? ORDER BY created_at DESC", (project_id,)))

            return {
                **p,
                "repo": repo,
                "documents": docs,
                "findings": findings_list,
                "gates": gates_list,
                "runs": recent_runs,
                "memories": mems,
            }

    def find_project_by_name(self, query: str) -> Optional[Dict[str, Any]]:
        with db() as con:
            # Exact match first
            p = row(con.execute("SELECT id FROM projects WHERE LOWER(name) = LOWER(?)", (query.strip(),)))
            if not p:
                # Substring match
                p = row(con.execute("SELECT id FROM projects WHERE LOWER(name) LIKE ? OR LOWER(id) LIKE ? LIMIT 1", (f"%{query.strip().lower()}%", f"%{query.strip().lower()}%")))
            if p:
                return self.get_project(p["id"])
            return None

    def get_document_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        with db() as con:
            doc = row(con.execute("SELECT * FROM documents WHERE id = ?", (document_id,)))
            if not doc:
                return None
            ver = row(con.execute("SELECT * FROM document_versions WHERE document_id = ? AND version = ?", (document_id, doc["current_version"])))
            return {
                **doc,
                "version_data": ver
            }

    def list_all_skills_manifest(self) -> List[Dict[str, Any]]:
        """Returns metadata about registered QE skills from database and local catalog."""
        with db() as con:
            return rows(con.execute("SELECT * FROM settings WHERE key LIKE 'skill_%'"))

    def add_memory(self, project_id: str, content: str, author: str = "Harness Agent") -> Dict[str, Any]:
        with db() as con:
            mid = new_id("mem")
            ts = now()
            con.execute("INSERT INTO memories (id, project_id, content, created_at) VALUES (?, ?, ?, ?)", (mid, project_id, content, ts))
            return {"id": mid, "project_id": project_id, "content": content, "created_at": ts}


global_project_repo = ProjectRepository()
