"""Change workflow gate and delivery: the patch for a human to review, then the commit, finding marks and optional pull request."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.config import repo_dir
from backend.core import documents
from backend.db import db
from backend.maf.engine import RunContext
from backend.repos import git, github, ingest


def change_gate(rc: RunContext, state: dict):
    worktree = Path(state["worktree"])
    patch = git.diff(worktree)
    doc = documents.create(rc.project_id, "patch", state["title"], patch or "(no changes)", f"agent:{state.get('kind', 'feature')}", note=state.get("summary", ""), run_id=rc.run_id, data=state.get("verification"))
    state["patch_doc"] = doc["id"]
    verdict = state["verification"]["verdict"]
    can_pr = bool((repo := ingest.get(rc.project_id)) and repo["credential_id"] and github.parse_slug(repo["url"]))
    return {"title": f"Review change: {state['title']}", "summary": f"Test verdict {verdict}. {state.get('summary', '')}",
            "payload": {"diff": patch[:60000], "patch_document": doc["id"], "branch": state["branch"], "verification": state["verification"], "can_open_pr": can_pr}}


async def change_deliver(rc: RunContext, state: dict, answer: dict) -> dict:
    worktree = Path(state["worktree"])
    commit = await asyncio.to_thread(git.commit_all, worktree, f"{state['title']}\n\n{state.get('summary', '')}\n\nApproved by {answer['by']} in Agentic QE Platform run {rc.run_id}")
    rc.log(f"Committed {commit[:10]} on {state['branch']}", kind="artifact")
    outcome = {"commit": commit}
    if state.get("finding_ids"):
        changed = await asyncio.to_thread(git.run, ["diff", "--name-only", "HEAD~1", "HEAD"], worktree)
        marks = [(i, name) for i in state["finding_ids"] for name in changed.splitlines()]
        # a change whose tests did not pass has not been shown to fix anything, so its findings stay open as "fix attempted"
        verdict = state["verification"]["verdict"]
        status = "fixed" if verdict in {"PASS", "NO NEW FAILURES"} else "fix_attempted"
        with db() as con:
            done = sum(con.executemany("UPDATE findings SET status=? WHERE id=? AND file=?", [(status, *m) for m in marks]).rowcount for _ in [0])
        rc.log(f"Marked {done} findings as {status.replace('_', ' ')} (test verdict {verdict}). Findings in unchanged files stay open", kind="artifact")
    repo = ingest.get(rc.project_id)
    if answer.get("open_pr") and repo and repo["credential_id"]:
        slug = github.parse_slug(repo["url"])
        if slug:
            token = github.token_for(repo["credential_id"])
            await asyncio.to_thread(git.push, worktree, state["branch"], token)
            base = repo["ref"] or await asyncio.to_thread(git.run, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo_dir(rc.project_id), None, 30, False)
            pr = await github.open_pr(token, slug[0], slug[1], state["branch"], (base or "main").removeprefix("origin/"), state["title"], f"{state.get('summary', '')}\n\nTest verdict: {state['verification']['verdict']}\nApproved by {answer['by']}.")
            outcome["pull_request"] = pr
            rc.log(f"Opened pull request {pr['url']}", pr, "artifact")
    return outcome
