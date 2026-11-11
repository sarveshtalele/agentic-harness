"""MAF context provider that puts project facts in front of every agent run."""
from __future__ import annotations

from agent_framework import ContextProvider

from backend.core import documents
from backend.db import db, rows
from backend.repos import ingest


class ProjectContext(ContextProvider):
    """MAF context provider: injects project facts, repo summary, memories, and the document index."""

    def __init__(self, project_id: str, full: bool = True):
        super().__init__("project-context")
        self.project_id, self.full = project_id, full

    async def before_run(self, *, agent, session, context, state) -> None:
        with db() as con:
            row = con.execute("SELECT name, description FROM projects WHERE id=?", (self.project_id,)).fetchone()
            project = dict(row) if row else {"name": self.project_id, "description": ""}
            memories = rows(con.execute("SELECT content FROM memories WHERE project_id=? ORDER BY created_at DESC LIMIT 25", (self.project_id,)))
        repo = ingest.get(self.project_id)
        parts = [f"Project: {project['name']}. {project['description']}".strip()]
        if repo:
            a = repo["analysis"]
            parts.append(f"Repository ({repo['kind']}: {repo['url']}, commit {repo['commit_sha'][:10]}): languages {a['languages']}, frameworks {a['frameworks']}, test runners {a['test_runners']}, {a['total_files']} files, {a['test_file_count']} test files.")
        else:
            parts.append("No repository connected.")
        # workflow agents get a precise task; a document list only tempts them to wander off it
        docs = documents.list_for(self.project_id)[:30] if self.full else []
        if docs:
            parts.append("Saved documents: " + "; ".join(f"{d['id']} [{d['kind']}] {d['title']} v{d['current_version']} ({d['status']})" for d in docs))
        if memories and self.full:
            parts.append("Remembered facts for this project:\n" + "\n".join(f"- {m['content']}" for m in memories))
        context.extend_instructions(self.source_id, "\n".join(parts))
