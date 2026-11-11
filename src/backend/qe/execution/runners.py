"""Registered test runners, JUnit parsing, honest verdicts."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


SENSITIVE_ENV = re.compile(r"(?i)key|token|secret|password|credential|auth|cookie")


TAIL = 6000


GIT_AUTHOR = "Agentic QE Platform"


def clean_env(extra: dict | None = None) -> dict:
    """Test code from the target repo must never see this platform's credentials."""
    env = {k: v for k, v in os.environ.items() if not SENSITIVE_ENV.search(k)}
    env.update(extra or {})
    return env


def parse_junit(xml_text: str) -> dict:
    empty = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "cases": []}
    if not xml_text.strip():
        return empty
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return empty
    cases = []
    for node in root.iter("testcase"):
        failure = node.find("failure")
        if failure is None:
            failure = node.find("error")
        skipped = node.find("skipped") is not None
        cases.append({
            "name": node.get("name", ""), "classname": node.get("classname", ""), "time": float(node.get("time") or 0),
            "status": "failed" if failure is not None else "skipped" if skipped else "passed",
            "message": ((failure.get("message") or "") + "\n" + (failure.text or ""))[:3000] if failure is not None else "",
        })
    failed = sum(c["status"] == "failed" for c in cases)
    skipped = sum(c["status"] == "skipped" for c in cases)
    return {"total": len(cases), "passed": len(cases) - failed - skipped, "failed": failed, "skipped": skipped, "cases": cases}


def verdict(result: dict, exit_code: int | None) -> str:
    """Port of run-isolated.ts: zero executed tests is INCONCLUSIVE, never PASS."""
    executed = result["passed"] + result["failed"]
    if exit_code is None or executed == 0:
        return "INCONCLUSIVE"
    return "FAIL" if result["failed"] or exit_code != 0 else "PASS"


def detect_python(worktree: Path) -> str:
    venv = worktree.parent / ".venv"
    candidate = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(candidate) if candidate.exists() else sys.executable


def _pytest(worktree: Path, target: str, junit: Path, extra: tuple[str, ...] = ()) -> list[str]:
    return [detect_python(worktree), "-m", "pytest", target, "-q", "--tb=short", "-p", "no:cacheprovider", "--continue-on-collection-errors", f"--junitxml={junit}", *extra]


def _node_tool(name: str, *args: str) -> list[str] | None:
    npx = shutil.which("npx")
    return [npx, "--no-install", name, *args] if npx else None


def build_command(runner: str, worktree: Path, target: str, junit: Path, extra: tuple[str, ...] = ()) -> tuple[list[str] | None, dict]:
    env: dict = {}
    if runner == "pytest":
        pypaths = [str(worktree)]
        for sub in ("backend", "src", "server", "app"):
            cand = worktree / sub
            if cand.is_dir():
                pypaths.append(str(cand))
        existing_pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(pypaths) + (os.pathsep + existing_pp if existing_pp else "")
        return _pytest(worktree, target, junit, extra), env
    if runner == "vitest":
        return _node_tool("vitest", "run", target, "--reporter=junit", f"--outputFile={junit}"), env
    if runner == "jest":
        return _node_tool("jest", target, "--ci", "--reporters=default", "--reporters=jest-junit"), {"JEST_JUNIT_OUTPUT_FILE": str(junit)}
    if runner == "playwright":
        return _node_tool("playwright", "test", target, "--reporter=junit"), {"PLAYWRIGHT_JUNIT_OUTPUT_NAME": str(junit)}
    return None, env


REGISTERED = ("pytest", "vitest", "jest", "playwright")


def pick_runner(framework: str, tests: list[str]) -> tuple[str, str]:
    """The runner for the generated tests, decided by code. The model's framework label counts only when it names a
    registered runner; otherwise the files decide (a model once wrote "python", so nothing ran and the verdict was
    INCONCLUSIVE). Returns (runner, note), where note says when the label was not used.

    ponytail: JavaScript files with an unknown label stay unresolved, since vitest and jest both read *.test.ts.
    """
    label = (framework or "").lower()
    named = next((r for r in REGISTERED if r in label), "")
    if named:
        return named, ""
    if tests and all(t.endswith(".py") for t in tests):
        return "pytest", f"Framework label {framework!r} names no runner; the generated files are Python, so pytest runs them"
    return label, f"Framework label {framework!r} names no runner and the generated files do not decide one"


def run_suite(runner: str, worktree: Path, target: str, results_dir: Path, timeout: int = 300, extra: tuple[str, ...] = ()) -> dict:
    """`extra` is added to the pytest command line only, so the setup step can set options for generated tests without editing the repository's config."""
    if runner not in REGISTERED:
        return {"runner": runner, "target": target, "verdict": "INCONCLUSIVE", "reason": f"Runner {runner} is not registered", "exit_code": None, "total": 0, "passed": 0, "failed": 0, "skipped": 0, "cases": [], "output": ""}
    results_dir.mkdir(parents=True, exist_ok=True)
    junit = results_dir / f"{runner}-{int(time.time() * 1000)}.xml"
    command, env = build_command(runner, worktree, target, junit, extra)
    if not command:
        return {"runner": runner, "target": target, "verdict": "INCONCLUSIVE", "reason": "Node.js tooling not found on PATH", "exit_code": None, "total": 0, "passed": 0, "failed": 0, "skipped": 0, "cases": [], "output": ""}
    started = time.time()
    try:
        # no bytecode: a same-size edit within a second could otherwise run stale code, and cache files would enter the reviewed diff
        done = subprocess.run(command, cwd=worktree, env=clean_env({**env, "PYTHONDONTWRITEBYTECODE": "1"}), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        exit_code, output, reason = done.returncode, done.stdout + done.stderr, ""
    except subprocess.TimeoutExpired as exc:
        exit_code, output, reason = None, str(exc.stdout or ""), f"Timed out after {timeout}s"
    except OSError as exc:
        exit_code, output, reason = None, "", f"Could not start {runner}: {exc}"
    result = parse_junit(junit.read_text(encoding="utf-8", errors="replace")) if junit.exists() else parse_junit("")
    return {"runner": runner, "target": target, "verdict": verdict(result, exit_code), "reason": reason, "exit_code": exit_code,
            "duration_s": round(time.time() - started, 2), "command": " ".join(Path(command[0]).name if i == 0 else c for i, c in enumerate(command)),
            "output": output[-TAIL:], **result}
