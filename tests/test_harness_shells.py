"""Real shells for the harness (docs/PHASE2_PLAN.md section 5): persistent Bash and PowerShell sessions, background tasks.

Runs on macOS, Linux and Windows CI. A shell missing on a machine is skipped by name (Windows has bash only with Git for
Windows; PowerShell 7 is on every GitHub runner), never to hide a failure.
"""
import asyncio
import sys
import time
from types import SimpleNamespace

import pytest

from backend.maf.harness_kit import bg_tasks, shells

HAS_BASH, HAS_PWSH = bool(shells.find_bash()), bool(shells.find_powershell())
PY = sys.executable.replace("\\", "/")


@pytest.fixture
def ws(tmp_path, monkeypatch):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.py").write_text("x = 1\nreturn_me = 2\n", encoding="utf-8")
    monkeypatch.setattr(shells.ledger, "append", lambda *a, **k: None)
    monkeypatch.setattr(bg_tasks.ledger, "append", lambda *a, **k: None)
    return SimpleNamespace(project_id="prj_t", thread_id=f"thr_{time.monotonic_ns()}", user_id="u", root=tmp_path.resolve(), env=lambda: {})


def run(ws, kind, *commands, timeout_ms=None):
    async def go():
        try:
            return [await shells.run(ws, kind, c, timeout_ms) for c in commands]
        finally:
            await shells.close_thread(ws.thread_id)
    return asyncio.run(go())


@pytest.mark.skipif(not HAS_BASH, reason="no bash on this machine")
def test_bash_keeps_cd_and_variables_and_runs_pipelines(ws):
    first, second, piped = run(ws, "bash", "cd app && export GREETING=hello", "pwd; echo $GREETING", "grep -c return app/a.py | tr 1 Z || true")
    assert "exit code 0" in first
    assert "app" in second.splitlines()[0] and "hello" in second
    assert "exit code 0" in piped


@pytest.mark.skipif(not HAS_BASH, reason="no bash on this machine")
def test_bash_timeout_exit_one_spill_and_leaving_the_workspace(ws):
    timed, nomatch, big, outside, where = run(ws, "bash", "sleep 5", "grep nothing-here app/a.py", f"\"{PY}\" -c \"print('x' * 40000)\"",
                                              "cd /", "pwd", timeout_ms=2000)
    assert "Timed out after 2 s" in timed and "run_in_background" in timed
    assert "exit code 1 (no matches" in nomatch
    assert "saved in .aqh/out/" in big and len(big) < 3000
    saved = next(ws.root.glob(".aqh/out/*.txt"))
    assert saved.read_text(encoding="utf-8").count("x") >= 40000
    assert "Shell cwd was reset" in outside and where.splitlines()[0].rstrip("/").endswith(ws.root.name)


@pytest.mark.skipif(not HAS_PWSH, reason="no PowerShell on this machine")
def test_powershell_keeps_location_and_variables(ws):
    first, second = run(ws, "powershell", "Set-Location app; $env:GREETING = 'hello'", "(Get-Location).Path; $env:GREETING")
    assert "exit code 0" in first
    assert "app" in second and "hello" in second


@pytest.mark.skipif(not (HAS_BASH or HAS_PWSH), reason="no shell on this machine")
def test_background_task_reports_output_once_and_stops_on_request(ws):
    kind, program = next(iter(shells.available().items()))
    command = f"& \"{PY}\" -u -c \"import time; print('server up'); time.sleep(60)\"" if kind == "powershell" else f"\"{PY}\" -u -c \"import time; print('server up'); time.sleep(60)\""
    started = bg_tasks.start(ws, kind, program, command, "test server")
    task_id = started.split()[3]
    deadline = time.monotonic() + 30
    notes = []
    while time.monotonic() < deadline and not notes:
        notes = bg_tasks.updates(ws.thread_id)
        time.sleep(0.3)
    assert notes and "server up" in notes[0] and "running" in notes[0]
    assert bg_tasks.updates(ws.thread_id) == []  # each line is passed on once
    assert "ended" in bg_tasks.stop(ws.thread_id, task_id)
    assert "server up" in bg_tasks.output(ws.thread_id, task_id)
    bg_tasks.stop_all(ws.thread_id)


@pytest.mark.skipif(not (HAS_BASH or HAS_PWSH), reason="no shell on this machine")
def test_background_task_stops_at_its_time_limit(ws):
    kind, program = next(iter(shells.available().items()))
    command = f"& \"{PY}\" -c \"import time; time.sleep(60)\"" if kind == "powershell" else f"\"{PY}\" -c \"import time; time.sleep(60)\""
    task_id = bg_tasks.start(ws, kind, program, command, "sleeper", timeout_ms=1000).split()[3]
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and "ended" not in bg_tasks.output(ws.thread_id, task_id):
        time.sleep(0.3)
    assert "minute limit" in bg_tasks.output(ws.thread_id, task_id)
