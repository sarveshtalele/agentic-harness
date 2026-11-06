"""QE Heal Stage: Automated defect diagnostics and selector/fixture self-healing."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from pydantic import BaseModel, Field

from backend.core.errors import AllowanceError
from backend.core.security import safe_path
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.edits import ChangeSet, Edit, guarded_apply
from backend.maf.workflows.shared import code_pack
from backend.qe import execution


class DefectNote(BaseModel):
    test: str
    cause: str = ""
    fix: str = ""


class HealResult(ChangeSet):
    notes: list[DefectNote] = Field(default_factory=list)


def _records(results: list[dict], notes: dict, healed: set[str]) -> list[dict]:
    failed = [c for suite in results for c in suite["cases"] if c["status"] == "failed"]
    return [execution.failure_record(c, execution.classify_failure(c["message"]), c["name"] in healed, notes.get(c["name"]) or notes.get(f"{c['classname']}::{c['name']}")) for c in failed]


async def qe_heal(rc: RunContext, state: dict) -> dict:
    worktree = Path(state["worktree"])
    failures = [c for suite in state["results"] for c in suite["cases"] if c["status"] == "failed"]
    classified = [{**c, "class": execution.classify_failure(c["message"])} for c in failures]
    defects = [c for c in classified if c["class"] == "DEFECT"]
    drift = [c for c in classified if c["class"] in {"SELECTOR_DRIFT", "FIXTURE_DRIFT"}]
    rc.log(f"{len(defects)} application defects left failing, {len(drift)} drift, {len(classified) - len(defects) - len(drift)} environment", {"classes": [{"test": c["name"], "class": c["class"]} for c in classified]}, "review")
    log = [*state.get("healer_log", [])]
    notes = dict(state.get("defect_notes", {}))
    known = {n for c in classified for n in (c["name"], f"{c['classname']}::{c['name']}")}

    def healing_guard(edit: Edit) -> str | None:
        target = safe_path(worktree, edit.path)
        old = target.read_text(encoding="utf-8") if target.is_file() else ""
        new = edit.content if edit.action == "create" else old.replace(edit.search, edit.replace, 1)
        ok, reason = execution.assertions_preserved(old, new)
        if not edit.path.replace("\\", "/").startswith("tests/"):
            reason, ok = "Healing may only touch tests", False
        elif ok and not execution.heal_allowed(classified, edit.path):
            reason, ok = "Healing may only repair a test that failed from selector or fixture drift. An application defect stays a failing test", False
        return None if ok else reason

    applied: list[str] = []
    if classified:
        shown = json.dumps([{"test": f"{c['classname']}::{c['name']}", "class": c["class"], "message": c["message"][:700]} for c in classified[:30]])[:12000]
        ask = ("Repair only test drift in these failing tests. Never change an assertion's meaning. The line numbers are not part of the files. Also send one note per failing test: its test name, the cause shown by the message, and the fix. "
               "The class of each failure is decided by code and is not yours to change; an application defect gets no edit.\n" if drift else
               "No test here is drift, so send no edits. Send one note per failing test: its test name, the cause shown by the message, and the fix. The class is decided by code.\n")
        try:
            result = await AgentCall(rc.run_id, rc.project_id, "defect-diagnostician").typed(f"{ask}FAILURES:\n{shown}\n\nCODE:\n{code_pack(rc.project_id, worktree, limit=30_000)}", HealResult)
        except AllowanceError:
            raise
        except Exception as exc:
            if drift:
                raise
            rc.log(f"The defect notes did not run, so the pattern text is used: {str(exc)[:200]}", kind="warning")
            result = HealResult(summary="")
        for note in result.notes:
            if note.test in known:
                notes[note.test] = {"cause": note.cause, "fix": note.fix}
        if drift:
            applied, refused = await asyncio.to_thread(guarded_apply, worktree, result.edits, healing_guard)
            log.append({"applied": applied, "refused": refused, "summary": result.summary[:500]})
            rc.log(f"Healed {applied}; refused {refused}", kind="artifact")
    healed = {c["name"] for c in drift if any(Path(a).stem and re.search(rf"(?<![a-z0-9]){re.escape(Path(a).stem.lower())}(?![a-z0-9])", re.sub(r"[^a-z0-9]+", "_", f"{c['classname']} {c['name']}".lower())) for a in applied)}
    records = _records(state["results"], notes, healed)
    update = {"heal_attempts": state.get("heal_attempts", 0) + 1, "defects": [{"name": c["name"], "message": c["message"][:1500]} for c in defects], "defect_notes": notes, "defect_records": records, "healer_log": log}
    return {**update, "_next": "execute" if applied else "trace"}
