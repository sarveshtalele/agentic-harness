"""Harness discovery eval scoring (docs/PHASE2_PLAN.md section 8, step 1 of section 16).

One task is a prompt plus what a good run looks like. A run is the list of tool calls (name, arguments, result) the harness
made and its final answer. Scoring is pure and deterministic, so the same trace always gives the same numbers:
- selected: some call used one of the task's expected tools (`tools`);
- first_ok: the first call that was not a plain look-around read used an expected tool;
- invalid_args: calls refused for their arguments;
- invented: calls to a tool name the harness does not have;
- refused: calls the harness or a hook refused;
- passed: the task's own check held (answer text, a file on disk, or a command's output).
"""
from __future__ import annotations

import re
from pathlib import Path

INVALID = re.compile(r"Error \[invalid_arguments\]|validation error|unexpected keyword|Extra inputs are not permitted|missing \d+ required|"
                     r"Field required", re.I)
INVENTED = re.compile(r"(function|tool)\s+['\"`]?[\w.-]+['\"`]?\s+(was\s+)?not found|unknown tool|no tool named|is not a known tool", re.I)
REFUSED = re.compile(r"^(Refused|Blocked)\b")
LOOK_AROUND = frozenset({"list_files", "file_access_ls", "glob", "find_tools", "load_tools", "todos_add", "todos_list", "todos_complete",
                         "project_status", "sandbox_status"})


def score(task: dict, calls: list[dict], answer: str, root: Path | None) -> dict:
    """`calls`: [{"name", "args", "result"}] in order. `root`: the workspace the run used, for file checks."""
    expected = set(task.get("tools", []))
    names = [c["name"] for c in calls]
    acting = [n for n in names if n not in LOOK_AROUND] or names
    checks = task.get("check", {})
    passed, why = _check(checks, answer, root)
    return {
        "id": task["id"], "kind": task.get("kind", ""),
        "calls": len(calls), "tools_used": sorted(set(names)),
        "selected": bool(expected & set(names)) if expected else True,
        "first_ok": (acting[0] in expected) if expected and acting else not expected,
        "invalid_args": sum(1 for c in calls if INVALID.search(str(c.get("result", "")))),
        "invented": sum(1 for c in calls if INVENTED.search(str(c.get("result", "")))),
        "refused": sum(1 for c in calls if REFUSED.search(str(c.get("result", "")).lstrip())),
        "passed": passed, "why": why,
    }


def _check(checks: dict, answer: str, root: Path | None) -> tuple[bool, str]:
    text = answer.lower()
    if any_of := checks.get("answer_any"):
        if not any(a.lower() in text for a in any_of):
            return False, f"answer has none of {any_of}"
    if all_of := checks.get("answer_all"):
        missing = [a for a in all_of if a.lower() not in text]
        if missing:
            return False, f"answer lacks {missing}"
    for rel, needle in (checks.get("file_contains") or {}).items():
        path = (root / rel) if root else None
        if path is None or not path.is_file():
            return False, f"{rel} missing"
        if needle and needle not in path.read_text(encoding="utf-8", errors="replace"):
            return False, f"{rel} lacks {needle!r}"
    for rel, needle in (checks.get("file_lacks") or {}).items():
        path = (root / rel) if root else None
        if path is not None and path.is_file() and needle in path.read_text(encoding="utf-8", errors="replace"):
            return False, f"{rel} still has {needle!r}"
    return True, "ok"


def aggregate(scores: list[dict]) -> dict:
    n = len(scores) or 1
    calls = sum(s["calls"] for s in scores) or 1
    return {
        "tasks": len(scores),
        "passed": sum(s["passed"] for s in scores),
        "pass_rate": round(sum(s["passed"] for s in scores) / n, 3),
        "selection_rate": round(sum(s["selected"] for s in scores) / n, 3),
        "first_try_rate": round(sum(s["first_ok"] for s in scores) / n, 3),
        "arg_validity": round(1 - sum(s["invalid_args"] for s in scores) / calls, 3),
        "invented_names": sum(s["invented"] for s in scores),
        "refused_calls": sum(s["refused"] for s in scores),
        "calls_per_task": round(calls / n, 1),
    }
