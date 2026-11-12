"""Settings files and hooks (docs/PHASE2_PLAN.md section 9.3 and 9.4): layers and trust, hooks from the user's settings,
updatedInput, http hooks, Stop hooks in the loop, and PostToolUseFailure."""
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

from backend import config
from backend.core import plugin_hooks, settings_files
from backend.maf.harness_kit import hook_middleware, stop_hooks

DENY = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "no curl here"}}


@pytest.fixture
def layered(tmp_path, monkeypatch):
    home, repo = tmp_path / "home", tmp_path / "repo"
    (home / ".aqh").mkdir(parents=True)
    (repo / ".claude").mkdir(parents=True)
    monkeypatch.setattr(settings_files.Path, "home", lambda: home)
    monkeypatch.setattr(settings_files, "managed_path", lambda: tmp_path / "managed.json")
    monkeypatch.setattr(config, "PROFILE", "desktop")
    monkeypatch.setattr(plugin_hooks.ledger, "append", lambda *a, **k: None)
    monkeypatch.setattr(plugin_hooks.plugins, "discover", lambda *a, **k: [])  # only settings-file hooks in these tests
    return SimpleNamespace(home=home, repo=repo, managed=tmp_path / "managed.json", tmp=tmp_path)


def hook_script(folder, output: dict, exit_code: int = 0) -> str:
    script = folder / f"hook_{len(list(folder.glob('hook_*.py')))}.py"
    script.write_text(f"import json, sys\nsys.stdin.read()\nprint(json.dumps({output!r}))\nsys.exit({exit_code})\n", encoding="utf-8")
    return f'"{sys.executable}" "{script}"'


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_layers_trust_managed_and_user_but_let_the_repository_only_tighten(layered):
    write(layered.managed, {"permissions": {"deny": ["Bash(curl *)"]}})
    write(layered.home / ".aqh" / "settings.json", {"permissions": {"allow": ["Bash(npm test)"]}})
    write(layered.repo / ".claude" / "settings.json", {"permissions": {"allow": ["Bash"], "ask": ["Bash(git push *)"]},
                                                       "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo x"}]}]}})
    rules = settings_files.permission_rules(layered.repo)
    assert rules == {"allow": ["Bash(npm test)"], "ask": ["Bash(git push *)"], "deny": ["Bash(curl *)"]}
    assert settings_files.hooks("PreToolUse", layered.repo) == []  # repository hooks wait for folder trust


def test_a_user_settings_hook_blocks_and_another_rewrites_the_input(layered):
    write(layered.home / ".aqh" / "settings.json", {"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": hook_script(layered.tmp, DENY)}]}]}})
    outcome = plugin_hooks.dispatch("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "curl x"}}, project_id="p", project_dir=layered.repo,
                                    tool_name="Bash")
    assert outcome.blocked and outcome.reason == "no curl here"
    rewrite = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {"command": "npm test -- --ci"}}}
    write(layered.home / ".aqh" / "settings.json", {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": hook_script(layered.tmp, rewrite)}]}]}})
    outcome = plugin_hooks.dispatch("PreToolUse", {"tool_name": "Bash"}, project_id="p", project_dir=layered.repo, tool_name="Bash")
    assert not outcome.blocked and outcome.updated_input == {"command": "npm test -- --ci"}
    call = SimpleNamespace(arguments={"command": "npm test", "description": "tests"})
    hook_middleware._apply(call, "bash", outcome.updated_input)
    assert call.arguments == {"command": "npm test -- --ci", "description": "tests"}
    write_call = SimpleNamespace(arguments={"file_name": "a.py", "content": "x"})
    hook_middleware._apply(write_call, "file_access_write", {"file_path": "/etc/passwd", "content": "y"})
    assert write_call.arguments == {"file_name": "a.py", "content": "y"}  # a hook may not redirect a write


def test_http_hooks_post_json_and_plain_http_is_local_only(layered):
    class Deny(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = json.dumps(DENY).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Deny)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/hook"
        write(layered.home / ".aqh" / "settings.json", {"hooks": {"PreToolUse": [{"hooks": [{"type": "http", "url": url}]},
                                                                                 {"hooks": [{"type": "http", "url": "http://example.com/hook"}]}]}})
        outcome = plugin_hooks.dispatch("PreToolUse", {"tool_name": "Bash"}, project_id="p", project_dir=layered.repo, tool_name="Bash")
    finally:
        server.shutdown()
    assert outcome.blocked and outcome.reason == "no curl here"
    assert any("must be https" in e for e in outcome.errors)  # refused, reported, never fatal


def test_stop_hooks_keep_the_loop_going_at_most_three_times(monkeypatch):
    monkeypatch.setattr(stop_hooks.plugin_hooks, "dispatch", lambda *a, **k: plugin_hooks.Outcome(blocked=True, reason="tests not run yet"))
    ws = SimpleNamespace(thread_id="t", project_id="p", root=".", env=lambda: {})
    check, message = stop_hooks.with_stop_hooks(ws, lambda **k: False, lambda **k: "todo note")
    rounds = [asyncio.run(check(last_result=SimpleNamespace(text="done"))) for _ in range(5)]
    assert rounds == [True, True, True, False, False]
    assert "todo note" == asyncio.run(message())  # after the limit the todo loop's own message applies again


def test_a_failed_tool_fires_post_tool_use_failure(tmp_path, monkeypatch):
    from agent_framework import Agent, tool

    from tests.helpers_harness import steps
    from tests.scripted_client import ScriptedClient

    events = []
    monkeypatch.setattr(hook_middleware.plugin_hooks, "dispatch", lambda event, *a, **k: events.append(event) or plugin_hooks.Outcome())

    @tool(name="file_access_write", description="Write a file.")
    def file_access_write(file_name: str, content: str) -> str:
        raise OSError("disk full")

    ws = SimpleNamespace(thread_id="thr_fail", project_id="prj_x", user_id="u", root=tmp_path, env=lambda: {})
    scripted = ScriptedClient([("go", steps({"call": "file_access_write", "args": {"file_name": "a.py", "content": "x"}}, "done"))])
    asyncio.run(Agent(scripted, tools=[file_access_write], middleware=[hook_middleware.guarded(ws)]).run("go"))
    assert events[:2] == ["PreToolUse", "PostToolUseFailure"]
