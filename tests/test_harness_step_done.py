"""A plugin step ends when its work is done (live QE cycle, 2026-11-13): discovery wrote both of its files at 82 seconds,
then kept adding todos and restarting the same analyst for another 1,000 seconds. Open todos no longer keep a turn going
once the active command's files are written and its own check passes."""
import asyncio
from types import SimpleNamespace

from backend.maf.harness_kit import active_command, stop_hooks, verify

FILES = ["docs/qe/app/01-discovery/summary.md", "docs/qe/app/01-discovery/architecture.json"]


def test_a_step_with_its_files_written_and_its_check_passing_ends_the_turn(tmp_path, monkeypatch):
    monkeypatch.setattr(stop_hooks.plugin_hooks, "dispatch", lambda *a, **k: stop_hooks.plugin_hooks.Outcome(blocked=False, reason=""))
    ws = SimpleNamespace(thread_id="thr_done", project_id="p", root=tmp_path, env=lambda: {})
    todos_open = lambda **k: True  # noqa: E731 - the model keeps adding todos
    discover = {"name": "agentic-qe:qe-discover", "args": "app", "paths": FILES, "check": None}
    check, _ = stop_hooks.with_stop_hooks(ws, todos_open, lambda **k: "todo note", command=discover)
    done = SimpleNamespace(text="Discovery written.")

    assert asyncio.run(check(last_result=done))  # nothing written yet: the todos keep it going
    (tmp_path / FILES[0]).parent.mkdir(parents=True)
    (tmp_path / FILES[0]).write_text("# Discovery\n", encoding="utf-8")
    assert asyncio.run(check(last_result=done))  # one of two files
    (tmp_path / FILES[1]).write_text("{}", encoding="utf-8")
    assert not asyncio.run(check(last_result=done))  # both written, no check: the step is done

    checked = {**discover, "check": ["node", "check-gate.ts"]}
    verify._last["thr_done"] = {"passed": False, "output": "FAIL: requirement R1 has no quote"}
    assert not active_command.step_done(checked, tmp_path, "thr_done")  # written but its check fails: keep fixing
    verify._last["thr_done"] = {"passed": True, "output": "PASS"}
    assert active_command.step_done(checked, tmp_path, "thr_done")
    assert not active_command.step_done({**discover, "paths": []}, tmp_path, "thr_done")  # a command that names no files (doctor)
