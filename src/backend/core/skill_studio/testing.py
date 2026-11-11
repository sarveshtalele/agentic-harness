"""Testing a draft for real: its own pytest files in a scratch copy, and deterministic eval assertions on model output."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from backend import config

TIMEOUT = 120
TAIL = 4000
WEB_REFUSAL = "Script runs are off on the shared web server; use the desktop app"
_COUNT = re.compile(r"(\d+) (passed|failed|error|errors)\b")


class ProfileRefused(PermissionError):
    """Answered 403: this server's profile does not run skill code."""


def check_profile() -> None:
    """Skill code is untrusted, so it runs only where the user's own machine pays for it."""
    if config.PROFILE not in ("local", "desktop"):
        raise ProfileRefused(WEB_REFUSAL)


def run_pytest(draft: Path) -> dict:
    """`python -m pytest -q scripts` in a temporary copy, with no shell, a timeout, and an environment stripped of secrets."""
    check_profile()
    from backend.repos.sandbox import clean_sandbox_env

    with tempfile.TemporaryDirectory(prefix="skill-test-") as scratch:
        copy = Path(scratch) / draft.name
        shutil.copytree(draft, copy, symlinks=False)
        try:
            done = subprocess.run([sys.executable, "-m", "pytest", "-q", "scripts"], cwd=copy, env=clean_sandbox_env(),
                                  capture_output=True, text=True, timeout=TIMEOUT, shell=False)
        except subprocess.TimeoutExpired as exc:
            return {"verdict": "FAIL", "exit_code": None, "passed": 0, "failed": 0, "errors": 0, "timed_out": True,
                    "stdout_tail": _text(exc.stdout)[-TAIL:], "stderr_tail": _text(exc.stderr)[-TAIL:], "detail": f"timed out after {TIMEOUT} s"}
    counts = {"passed": 0, "failed": 0, "errors": 0}
    summary = next((line for line in reversed(done.stdout.splitlines()) if _COUNT.search(line) or "no tests ran" in line), "")
    for number, word in _COUNT.findall(summary):
        counts["errors" if word.startswith("error") else word] += int(number)
    ran = counts["passed"] + counts["failed"]
    verdict = "INCONCLUSIVE" if ran == 0 and not counts["errors"] else "PASS" if done.returncode == 0 and counts["failed"] == counts["errors"] == 0 else "FAIL"
    return {"verdict": verdict, "exit_code": done.returncode, **counts, "timed_out": False, "summary": summary.strip(),
            "stdout_tail": done.stdout[-TAIL:], "stderr_tail": done.stderr[-TAIL:]}


def _text(value) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")


def grade(output: str, assertions: list[dict]) -> list[dict]:
    """contains and not_contains ignore case; regex is searched as written."""
    results = []
    for a in assertions:
        if a["kind"] == "contains":
            passed = a["value"].lower() in output.lower()
        elif a["kind"] == "not_contains":
            passed = a["value"].lower() not in output.lower()
        else:
            passed = re.search(a["value"], output) is not None
        results.append({**a, "passed": passed})
    return results


def rate(graded: list[list[dict]]) -> float:
    flat = [a for case in graded for a in case]
    return sum(a["passed"] for a in flat) / len(flat) if flat else 0.0
