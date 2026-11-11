"""Change workflow, first stage: an isolated worktree on its own branch, and the test results before any edit."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from backend.config import project_dir, repo_dir
from backend.db import db, rows
from backend.maf.engine import RunContext
from backend.qe import execution
from backend.repos import git


MAX_FIX_ALL = 15  # ponytail: one branch stays reviewable. Run Fix all again for the next set


def _chosen_findings(project_id: str, state: dict) -> list[dict]:
    with db() as con:
        if state.get("fix_all"):
            return rows(con.execute(f"SELECT * FROM findings WHERE project_id=? AND status IN ('open','fix_attempted') ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, file, line LIMIT {MAX_FIX_ALL}", (project_id,)))
        if state.get("finding_id"):
            return rows(con.execute("SELECT * FROM findings WHERE id=? AND project_id=?", (state["finding_id"], project_id)))
    return []


async def change_prepare(rc: RunContext, state: dict) -> dict:
    root = repo_dir(rc.project_id)
    if not root.exists():
        raise ValueError("Connect a repository or upload a ZIP first")
    if not state.get("spec", "").strip() and not state.get("finding_id") and not state.get("fix_all"):
        raise ValueError("Describe the change or pick a finding")
    spec = state.get("spec", "")
    findings = _chosen_findings(rc.project_id, state)
    if state.get("fix_all") and not findings:
        raise ValueError("There are no open findings to fix")
    if findings:
        listed = "\n".join(f"- Rule {f['rule']} ({f['severity']}): {f['title']}\n  Location: {f['file']}:{f['line']}\n  Evidence: {f['evidence']}\n  {f['explanation']}" for f in findings)
        spec = f"Fix {'these findings' if len(findings) > 1 else 'this finding'}.\n{listed}\n{spec}"
        state["findings_by_file"] = {name: "\n".join(f"- {f['severity']} at line {f['line']}: {f['title']}. Evidence: {f['evidence']}. {f['explanation']}" for f in findings if f["file"] == name) for name in {f["file"] for f in findings}}
        state["title"] = state.get("title") or (f"Fix {findings[0]['title'][:50]}" if len(findings) == 1 else f"Fix {len(findings)} findings")
    slug = re.sub(r"[^a-z0-9]+", "-", (state.get("title") or state.get("kind", "change")).lower()).strip("-")[:40] or "change"
    branch = f"atlas/{slug}-{rc.run_id[-6:]}"
    worktree = project_dir(rc.project_id) / "worktrees" / rc.run_id
    worktree.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(git.add_worktree, root, worktree, branch)
    rc.log(f"Isolated worktree on branch {branch}")
    # tests run before the change, so a repo that already fails is never blamed on the agent
    analysis = await asyncio.to_thread(_rescan, worktree)
    if state.get("install_deps"):
        await asyncio.to_thread(execution.install_dependencies, worktree, analysis, rc.log)
    baseline = {}
    for runner in execution.choose_runners(analysis):
        result = await asyncio.to_thread(execution.run_suite, runner, worktree, "." if runner == "pytest" else "", worktree.parent / f"{rc.run_id}-baseline")
        baseline[runner] = execution.failed_names(result)
        rc.log(f"Before the change, {runner}: {result['passed']} passed, {result['failed']} failed", {"reason": result["reason"]}, "test")
    return {"branch": branch, "worktree": str(worktree), "spec": spec, "attempt": 0, "baseline": baseline, "title": state.get("title") or slug, "finding_files": sorted({f["file"] for f in findings}), "finding_ids": [f["id"] for f in findings], "findings_by_file": state.get("findings_by_file", {})}


def _rescan(worktree: Path) -> dict:
    from backend.repos.scan import analyze

    return analyze(worktree)
