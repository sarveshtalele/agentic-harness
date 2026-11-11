"""The sandbox_status agent tool: where this project's repository, sandbox and run worktrees are, read from disk."""
from __future__ import annotations

import json

from agent_framework import tool

from backend.config import repo_dir
from backend.repos import sandbox

# Measured fields only; "sandbox_ready" is the same as "repository" here, so it is left out.
FIELDS = ("commit", "current_branch", "commits", "complete_history", "run_worktrees", "sandbox_initialized", "size_mb")


def build(project_id: str, thread_id: str, start_run):
    @tool(name="sandbox_status", description="Show this project's repository commit, sandbox state, branch, and run worktrees.")
    def sandbox_status() -> str:
        if not (repo_dir(project_id) / ".git").exists():
            return json.dumps({"repository": False, "reason": "No repository is connected to this project"})
        found = sandbox.info(project_id)
        return json.dumps({"repository": True, **{k: found[k] for k in FIELDS if k in found}})

    return sandbox_status
