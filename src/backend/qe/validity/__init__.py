"""Validity checks V3 to V6 for one generated test (docs/QE_V2_PLAN.md section 2). Code runs each check; none is a model's word."""
from __future__ import annotations

import re
from pathlib import Path

from backend.qe import emit, execution
from backend.qe.emit.subject import own_subject
from backend.qe.validity.assertions import integrity
from backend.qe.validity.collect import compiles

CHECKS = ("V3", "V4", "V5", "V6")
MARKER = re.compile(r"CASE_ID:\s*([A-Za-z0-9_.-]+)")


def _symbols(worktree: Path, path: str, code: str, inventory, allowed, async_ok: bool) -> dict:
    """V4: imports resolve and the symbols called exist, with signatures: emit.check plus the generation stage's import checks."""
    found = [*emit.check(worktree, path, code, inventory, allowed), *execution.invalid_test_code(worktree, path, code, async_ok), *own_subject(worktree, path, code)]
    found = list(dict.fromkeys(found))
    return {"status": "FAIL", "message": "; ".join(found[:4]) + ". Import only names the repository defines and call them with their real signature"} if found else {"status": "PASS", "message": "imports and called symbols exist"}


def _trace(path: str, code: str, case_ids: list[str], known: set[str]) -> dict:
    marked = set(MARKER.findall(code))
    if not marked:
        return {"status": "FAIL", "message": f"{path}: carries no case id. Put `# CASE_ID: {case_ids[0] if case_ids else '<case id>'}` on the first line"}
    if unknown := sorted(marked - known):
        return {"status": "FAIL", "message": f"{path}: CASE_ID {', '.join(unknown)} is not a case of this run. Use one of the designed case ids"}
    if missing := [c for c in case_ids if c not in marked]:
        return {"status": "FAIL", "message": f"{path}: does not carry its case id {', '.join(missing)}. Put `# CASE_ID: {missing[0]}` on the first line"}
    return {"status": "PASS", "message": f"carries {', '.join(sorted(marked))}"}


def check_file(worktree: Path, path: str, code: str, case_ids: list[str], cases: dict, *, inventory=None, allowed=frozenset(), async_ok: bool = False) -> dict[str, dict]:
    """{"V3": {status, message}, ...} for one test file. `cases` maps case id to its record."""
    expected = " ".join(cases.get(c, {}).get("expected_result", "") for c in case_ids)
    return {"V3": compiles(worktree, path, code), "V4": _symbols(worktree, path, code, inventory, allowed, async_ok),
            "V5": integrity(path, code, expected), "V6": _trace(path, code, case_ids, set(cases))}


def problems(checks: dict[str, dict]) -> list[str]:
    """What goes back to the test author: only failures. NOT CHECKED is not the author's fault."""
    return [f"{k} FAIL: {v['message']}" for k, v in checks.items() if v["status"] == "FAIL"]


def tally(tests: list[dict]) -> dict:
    """The run's result: per-test rows, counts by check, and the valid and invalid paths. A test is valid only when all four checks PASS."""
    for t in tests:
        t["valid"] = all(c["status"] == "PASS" for c in t["checks"].values())
    return {"tests": tests, "valid": [t["path"] for t in tests if t["valid"]], "invalid": [t["path"] for t in tests if not t["valid"]],
            "counts": {"total": len(tests), "valid": sum(t["valid"] for t in tests), "invalid": sum(not t["valid"] for t in tests),
                       **{k: sum(t["checks"][k]["status"] != "PASS" for t in tests) for k in CHECKS}}}


def line(validation: dict | None) -> str:
    if not validation:
        return ""
    c = validation["counts"]
    return f"Validity: {c['valid']} of {c['total']} tests valid; {c['invalid']} need review (V3 {c['V3']}, V4 {c['V4']}, V5 {c['V5']}, V6 {c['V6']})."
