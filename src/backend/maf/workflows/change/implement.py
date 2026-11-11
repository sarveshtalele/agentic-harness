"""Change workflow, implement stage: the agent edits the worktree, one file at a time when fixing several findings."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.core.errors import AllowanceError
from backend.core.security import safe_path
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.change.scope import _select_files, safe_exists, spec_gaps
from backend.maf.workflows.edits import ChangeSet, Edit, guarded_apply
from backend.maf.workflows.shared import code_pack
from backend.repos import git, scan


async def _fix_file_by_file(rc: RunContext, state: dict, worktree: Path) -> dict:
    """Fix all sends one small request per file. One long conversation grows with every round, and costs far more."""
    fixed, missed = [], []
    for name, listed in state["findings_by_file"].items():
        call = AgentCall(rc.run_id, rc.project_id, "defect-diagnostician", skills=())  # this fixes real defects; the healing skill would forbid that
        only_this_file = lambda edit, target=name: None if edit.path.replace("\\", "/") == target else f"Change only {target}."  # noqa: E731
        prompt = f"Fix these findings in {name}. Change only this file, and fix a finding only if it is a real defect.\nFINDINGS:\n{listed}\n\nCODE:\n{code_pack(rc.project_id, worktree, [name], 60_000)}"
        applied: list[str] = []
        try:
            for _ in range(2):
                result = await call.typed(prompt, ChangeSet)
                done, refused = await asyncio.to_thread(guarded_apply, worktree, result.edits, only_this_file)
                applied += done
                if not refused:
                    break
                prompt = f"These edits were refused: {refused}. Send only corrected edits. Each search must match the file exactly.\n\nCURRENT FILE:\n{code_pack(rc.project_id, worktree, [name], 60_000)}"
        except AllowanceError:
            raise
        except RuntimeError as exc:
            rc.log(f"Could not fix {name}: {exc}", kind="warning")
        (fixed if applied else missed).append(name)
        rc.log(f"{'Changed' if applied else 'No change to'} {name}", kind="artifact" if applied else "warning")
    if not fixed:
        raise RuntimeError(f"The agent did not change any of {', '.join(missed)}")
    summary = f"Changed {len(fixed)} of {len(fixed) + len(missed)} files with findings." + (f" Not changed: {', '.join(missed)}." if missed else "")
    rc.log(summary, kind="artifact")
    return {"summary": summary, "test_target": "", "attempt": state.get("attempt", 0) + 1, "feedback": "", "paths": await _select_files(rc, state, worktree)}


async def change_implement(rc: RunContext, state: dict) -> dict:
    worktree = Path(state["worktree"])
    if len(state.get("finding_files", [])) > 1 and not state.get("failure") and not state.get("feedback"):
        return await _fix_file_by_file(rc, state, worktree)
    agent = "defect-diagnostician" if state.get("kind") in {"bugfix", "diagnose"} else "feature-engineer"
    if not state.get("paths"):
        state["paths"] = await _select_files(rc, state, worktree)
    rc.log(f"Working on {len(state['paths'])} files", {"files": state["paths"]})
    message = f"TASK (do exactly this and nothing else):\n{state['spec']}\n\nCODE (current files, complete; you have no read tools and do not need them):\n{code_pack(rc.project_id, worktree, state['paths'], 60_000)}\n\nThe line numbers are not part of the files, so never put them in a search. Include a real test that fails without the change when the repo has a test setup.\n\nRepeat of the TASK: {state['spec'][:600]}"
    if state.get("failure"):
        message += f"\n\nThe last attempt broke these tests. Fix only this; do not touch unrelated code or tests.\nCurrent diff:\n{git.diff(worktree)[:8000]}\n\nFailures:\n{state['failure'][:5000]}"
    if state.get("feedback"):
        message += f"\n\nReviewer feedback on the last diff:\n{state['feedback']}\nCurrent diff:\n{git.diff(worktree)[:8000]}"
    finding_files = state.get("finding_files", [])

    def finding_scope(edit: Edit) -> str | None:
        """A finding's fix may change only that file and tests, so the agent cannot drift to another bug."""
        path = edit.path.replace("\\", "/")
        name = path.rsplit("/", 1)[-1]
        is_test = path.startswith("tests/") or name.startswith("test_")
        if finding_files and path not in finding_files and not is_test:
            return f"This task may only change {', '.join(finding_files)} and test files."
        if not safe_path(worktree, path).exists() and Path(path).suffix.lower() not in {*scan.LANGUAGES, ".json", ".yaml", ".yml", ".toml", ".md"}:
            return f"Refused new file {path}: only source, test, and configuration files belong in this change."
        return None

    call = AgentCall(rc.run_id, rc.project_id, agent, skills=())  # a real defect fix is not test healing
    before = git.diff(worktree)
    summary, prompt, paths = "", message, state["paths"]
    for _ in range(3):
        result = await call.typed(prompt, ChangeSet)
        summary = result.summary or summary
        applied, refused = await asyncio.to_thread(guarded_apply, worktree, result.edits, finding_scope)
        rc.log(f"Applied {applied or 'no edits'}" + (f"; refused {refused}" if refused else ""), kind="warning" if refused else "artifact")
        paths = [*paths, *[p for p in applied if p not in paths]]
        gaps = spec_gaps(worktree, state)
        changed = git.diff(worktree) != before
        # with several findings the agent may judge one a false alarm, so an untouched file alone is not worth another round. The verdict still lists it
        if changed and not refused and (not gaps or (len(finding_files) > 1 and all("a file with a finding" in g for g in gaps))):
            break
        prompt = f"Not finished. Refused edits: {refused or 'none'}. Missing: {gaps or ('no file changed yet' if not changed else 'nothing')}. Send only the remaining edits for this task: {state['spec'][:600]}\n\nCURRENT FILES:\n{code_pack(rc.project_id, worktree, sorted({r.split(":")[0] for r in refused if safe_exists(worktree, r.split(":")[0])}) or paths, 40_000)}"
    if git.diff(worktree) == before and not state.get("attempt"):
        raise RuntimeError("The agent finished without changing any file")
    # on a retry, keeping the earlier edits is valid: a person then reviews them with the honest failing verdict
    if finding_files and not set(finding_files) & set(git.run(["diff", "--name-only"], cwd=worktree).splitlines()):
        raise RuntimeError(f"The agent did not change {', '.join(finding_files)}, the files with the findings")
    rc.log(f"Changes applied: {summary[:300]}", kind="artifact")
    return {"summary": summary[:1000], "test_target": "", "attempt": state.get("attempt", 0) + 1, "feedback": "", "paths": state["paths"]}
