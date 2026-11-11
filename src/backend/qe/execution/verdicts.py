"""Execution summary checks and heal permission."""
from __future__ import annotations

import re
from pathlib import Path
from backend.qe.execution.failures import CLASSIFICATION, _first_line, classify_failure, failure_counts


def code_summary(result: dict) -> str:
    """The summary code writes itself. It is what is shown when the agent's summary is missing or refused."""
    text = f"{result['runner']}: {result['verdict']}. {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped."
    if result["failed"]:
        counts = failure_counts([result])
        text += f" Failures by class: {counts['defect']} defect, {counts['test problem']} test problem, {counts['environment']} environment. Environment failures count as not passed."
    return text + (f" {result['reason']}." if result.get("reason") else "")


def summary_evidence(result: dict, limit: int = 15) -> dict:
    """What the qa-execution-engineer is given: counts, the verdict, and the first failures with their class. Nothing else."""
    failures = [{"test": f"{c['classname']}::{c['name']}", "class": CLASSIFICATION[classify_failure(c["message"])], "first_line": _first_line(c["message"])[:200]}
                for c in result["cases"] if c["status"] == "failed"]
    return {"runner": result["runner"], "verdict": result["verdict"], "exit_code": result["exit_code"], "reason": result.get("reason", ""), "executed": result["passed"] + result["failed"],
            "passed": result["passed"], "failed": result["failed"], "skipped": result["skipped"], "failures_by_class": failure_counts([result]), "failures": failures[:limit], "failures_not_shown": max(0, len(failures) - limit)}


def summary_problems(claim: dict, result: dict) -> list[str]:
    """Checks the agent's summary against the JUnit counts. Any problem means the summary is refused."""
    problems = [f"it says {key} {claim.get(key)} but the report has {result[key]}" for key in ("passed", "failed", "skipped") if claim.get(key) != result[key]]
    if str(claim.get("verdict", "")).upper() != result["verdict"]:
        problems.append(f"it says the verdict is {claim.get('verdict')} but it is {result['verdict']}")
    text = str(claim.get("summary", ""))
    counted = {"passed": result["passed"], "failed": result["failed"], "errors": result["failed"], "error": result["failed"], "skipped": result["skipped"]}
    for number, word in re.findall(r"(\d+)\s+(passed|failed|skipped|errors?)\b", text, re.I):
        if int(number) != counted[word.lower()]:
            problems.append(f"its text says {number} {word} but the report has {counted[word.lower()]}")
    totals = {result["passed"] + result["failed"], result["passed"] + result["failed"] + result["skipped"]}
    for number in re.findall(r"(\d+)\s+(?:tests?|test cases)\b", text, re.I):
        if int(number) not in totals:
            problems.append(f"its text says {number} tests but the report has {' or '.join(map(str, sorted(totals)))}")
    for word in set(re.findall(r"\b(PASS|FAIL|INCONCLUSIVE)\b", text)):
        if word != result["verdict"]:
            problems.append(f"its text says {word} but the verdict is {result['verdict']}")
    return problems


def heal_allowed(failures: list[dict], path: str) -> bool:
    """Healing may change only a test file whose failure is drift, or a support file of the generated tests (fixtures, conftest). Never application code, never a test that found a defect."""
    path = path.replace("\\", "/")
    if not path.startswith("tests/"):
        return False
    if not re.search(r"(^|/)test_[^/]*\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$", path):
        return True
    norm = lambda text: re.sub(r"[^a-z0-9]+", "_", text.lower())
    mine = re.compile(rf"(?<![a-z0-9]){re.escape(norm(Path(path).stem))}(?![a-z0-9])")
    return any(f["class"] in {"SELECTOR_DRIFT", "FIXTURE_DRIFT"} and mine.search(norm(f"{f['classname']} {f['name']}")) for f in failures)
