"""Testing a draft for real: its own pytest files in a scratch copy, and deterministic eval assertions on model output."""
from __future__ import annotations

import json
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
    result = {"verdict": verdict, "exit_code": done.returncode, **counts, "timed_out": False, "summary": summary.strip(),
              "stdout_tail": done.stdout[-TAIL:], "stderr_tail": done.stderr[-TAIL:]}
    _record(draft, verdict)
    return result


def _record_path(draft: Path) -> Path:
    return draft.parent / f"{draft.name}.tests.json"


def _record(draft: Path, verdict: str) -> None:
    """The verdict for exactly these files, so publish can tell whether the files it installs are the ones that passed."""
    from backend.core.skill_studio import checks  # local: checks imports nothing from here, but keep the module light
    _record_path(draft).write_text(json.dumps({"sha256": checks.digest(checks.read_files(draft)), "verdict": verdict}), encoding="utf-8")


def passing_problem(draft: Path) -> str:
    """Why a script skill may not be published yet, or "" when its own tests passed on exactly these files."""
    from backend.core.skill_studio import checks
    path = _record_path(draft)
    if not path.is_file():
        return "Run the skill's tests first: a script skill is published only after its own tests pass."
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("sha256") != checks.digest(checks.read_files(draft)):
        return "The files changed after the last test run. Run the skill's tests again."
    if record.get("verdict") != "PASS":
        return f"The skill's own tests did not pass (verdict {record.get('verdict')}). Generate again or fix the plan, then test."
    return ""


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


def _test_strength(files: list[dict]) -> tuple[int, int, list[str]]:
    """Test functions, assert statements, and weakening found in the skill's pytest files."""
    import ast
    tests = asserts = 0
    weak: list[str] = []
    for f in files:
        if not re.match(r"scripts/test_[\w-]+\.py$", f["path"]):
            continue
        try:
            tree = ast.parse(f["content"])
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                tests += 1
            if isinstance(node, ast.Assert):
                asserts += 1
                if isinstance(node.test, ast.Constant) and node.test.value:
                    weak.append(f"{f['path']}:{node.lineno} assert {node.test.value!r}")
            if isinstance(node, ast.Attribute) and node.attr in ("skip", "skipif", "xfail") and getattr(node.value, "id", "") in ("pytest", "mark"):
                weak.append(f"{f['path']}:{node.lineno} pytest.{node.attr}")
    return tests, asserts, weak


def weakened(before: list[dict], after: list[dict]) -> str:
    """Why a repair is refused, or "". A repair may fix code or a wrong expectation, never make the tests weaker (CLAUDE.md)."""
    t0, a0, _ = _test_strength(before)
    t1, a1, weak = _test_strength(after)
    if t1 < t0:
        return f"the repair removed tests ({t0} before, {t1} after)"
    if a1 < a0:
        return f"the repair removed assertions ({a0} before, {a1} after)"
    return f"the repair added a weak test: {', '.join(weak)}" if weak else ""


def run_entry(draft: Path, text: str) -> dict:
    """`python scripts/run.py` with the case input on standard input, in a temporary copy: how a script skill really behaves."""
    check_profile()
    from backend.repos.sandbox import clean_sandbox_env

    if not (draft / "scripts" / "run.py").is_file():
        return {"output": "", "exit_code": None, "detail": "This script skill has no scripts/run.py entry point. Plan and generate it again."}
    with tempfile.TemporaryDirectory(prefix="skill-run-") as scratch:
        copy = Path(scratch) / draft.name
        shutil.copytree(draft, copy, symlinks=False)
        try:
            done = subprocess.run([sys.executable, "scripts/run.py"], cwd=copy, input=text, env=clean_sandbox_env(),
                                  capture_output=True, text=True, timeout=TIMEOUT, shell=False)
        except subprocess.TimeoutExpired:
            return {"output": "", "exit_code": None, "detail": f"timed out after {TIMEOUT} s"}
    return {"output": done.stdout, "exit_code": done.returncode, "detail": done.stderr[-TAIL:]}
