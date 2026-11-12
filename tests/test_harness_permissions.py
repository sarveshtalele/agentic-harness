"""Permission modes and rules (docs/PHASE2_PLAN.md section 9), and the shells in a real harness turn."""
import json
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.maf import llm
from backend.maf.harness_kit import permissions, shells
from tests.helpers_harness import approve, interrupt_of, project_with_repo, steps, turn
from tests.scripted_client import ScriptedClient

RULES = {"allow": ["Bash(npm run *)", "Bash(git status)"], "ask": ["Bash(git push *)"], "deny": ["Bash(rm -rf *)", "Edit(.env)"]}


@pytest.mark.parametrize("tool,args,mode,verdict", [
    ("bash", {"command": "npm run test"}, "default", "allow"),
    ("bash", {"command": "npm run a | git status"}, "default", "allow"),  # each part has an allow rule
    ("bash", {"command": "npm run a && curl x"}, "default", "ask"),  # curl has none
    ("bash", {"command": "npm run a && rm -rf /"}, "bypass", "deny"),  # deny wins over everything, even bypass
    ("bash", {"command": "git push origin main"}, "bypass", "ask"),  # ask rules beat bypass
    ("powershell", {"command": "Get-ChildItem"}, "default", "ask"),
    ("powershell", {"command": "Get-ChildItem"}, "bypass", "allow"),
    ("file_access_write", {"file_name": "src/a.py"}, "default", "ask"),
    ("file_access_write", {"file_name": "src/a.py"}, "acceptEdits", "allow"),
    ("file_access_write", {"file_name": ".env"}, "acceptEdits", "deny"),
    ("bash", {"command": "ls"}, "plan", "deny"),
    ("bash", {"command": "ls"}, "auto", "ask"),  # shells still ask until the OS sandbox exists
])
def test_decisions_follow_claude_code_rules(tool, args, mode, verdict):
    assert permissions.decide(tool, args, mode, RULES)[0] == verdict


def test_repository_settings_can_only_tighten(tmp_path, monkeypatch):
    monkeypatch.setattr(permissions.Path, "home", lambda: tmp_path / "home")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash"], "deny": ["Bash(curl *)"]}}))
    rules = permissions.load_rules(tmp_path)
    assert rules["allow"] == [] and rules["deny"] == ["Bash(curl *)"]  # repository content is untrusted (CLAUDE.md)
    (tmp_path / "home" / ".aqh").mkdir(parents=True)
    (tmp_path / "home" / ".aqh" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(npm test)"]}}))
    assert permissions.load_rules(tmp_path)["allow"] == ["Bash(npm test)"]  # the person's own settings may allow


def test_modes_are_per_conversation_and_bypass_is_refused_on_web(tmp_path, monkeypatch):
    assert permissions.get_mode(tmp_path, "thr_a") == "default"
    assert "acceptEdits" in permissions.set_mode(tmp_path, "thr_a", "acceptedits")
    assert permissions.get_mode(tmp_path, "thr_a") == "acceptEdits" and permissions.get_mode(tmp_path, "thr_b") == "default"
    monkeypatch.setattr(permissions.config, "PROFILE", "web")
    assert "not allowed" in permissions.set_mode(tmp_path, "thr_a", "bypass")


def test_allow_and_deny_skip_the_card_and_deny_is_refused():
    call = SimpleNamespace(name="bash", parse_arguments=lambda: {"command": "rm -rf /tmp/x"})
    assert permissions.approval_rule(lambda: "default", lambda: RULES)(call) is True  # no card for a denied call...
    ask = SimpleNamespace(name="bash", parse_arguments=lambda: {"command": "curl x"})
    assert permissions.approval_rule(lambda: "default", lambda: RULES)(ask) is False


@pytest.mark.skipif(not shells.find_bash(), reason="no bash on this machine")
def test_a_harness_turn_runs_a_real_bash_pipeline_after_approval_and_mode_answers_without_the_model():
    scripted = ScriptedClient([("pipeline", steps({"call": "bash", "args": {"command": "echo shop | tr a-z A-Z", "description": "upper-case a word"}}, "done"))])
    llm.set_client_override(scripted)
    try:
        with TestClient(app) as client:
            assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
            project = project_with_repo(client, "Shell shop")
            thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
            events = turn(client, thread["id"], "run the pipeline", "r1")
            assert interrupt_of(events)  # the command waits for approval in the default mode
            done = approve(client, thread["id"], events, "r2")
            results = [e for e in done if e["type"] == "TOOL_CALL_RESULT"]
            assert results and "SHOP" in str(results[0]["content"]) and "exit code 0" in str(results[0]["content"])
            calls_before = len(scripted.calls)
            reply = turn(client, thread["id"], "/mode acceptEdits", "r3")
            text = "".join(e.get("delta", "") for e in reply if e["type"] == "TEXT_MESSAGE_CONTENT")
            assert "acceptEdits" in text and len(scripted.calls) == calls_before  # no model call
    finally:
        llm.set_client_override(None)
