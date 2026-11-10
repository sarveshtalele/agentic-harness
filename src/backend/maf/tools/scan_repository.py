"""The scan_repository agent tool: the platform's static analyzers on the project's repository, read-only."""
from __future__ import annotations

import asyncio
import json
from collections import Counter

from agent_framework import tool

from backend.config import repo_dir
from backend.repos import static_analysis


def _scan(project_id: str) -> dict:
    repo = repo_dir(project_id)
    if not repo.is_dir() or not any(repo.iterdir()):
        return {"status": "NotScanned", "reason": "No repository is connected to this project"}
    found = static_analysis.run_all(repo)
    return {"status": "Analyzed" if found else "NoFindings", "analyzers": ["ruff", "secrets", "js_rules", "manifests"],
            "count": len(found), "by_severity": dict(Counter(f["severity"] for f in found)),
            "findings": [{k: f[k] for k in ("severity", "rule", "title", "file", "line", "evidence")} for f in found[:40]],
            "note": "Read-only: findings are not saved. Start the bug_scan workflow to save and review them."}


def build(project_id: str, thread_id: str, start_run):
    @tool(name="scan_repository", description="Run the platform's static analyzers (ruff, secret scan, JavaScript rules, manifests) on this project's "
                                              "repository and return the findings with file and line. Read-only.")
    async def scan_repository() -> str:
        return json.dumps(await asyncio.to_thread(_scan, project_id))

    return scan_repository
