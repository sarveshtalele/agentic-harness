"""Plan H3 with the installed agentic-qe plugin's real hooks (Node 22.18+), a real git repository and only the model
replaced by ScriptedClient: the human's typed `approve gate 0 for <app>` reaches the plugin's own approval-hook.ts, which
starts the run and writes its `.qe/` ledger; the plugin's guard-bash.ts then blocks `rm -rf /` and its reason reaches the
model; the plugin's agents are background agents that only read; SubagentStop runs when one finishes."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from agent_framework import BackgroundAgentsProvider, FileAccessProvider
from fastapi.testclient import TestClient

from backend.app import app
from backend.config import sandbox_dir
from backend.core import plugin_hooks
from backend.maf import engine, harness, llm
from tests.helpers_harness import NEEDLE, approve, ledger_rows, project_with_repo, steps, turn
from tests.scripted_client import ScriptedClient

APP = "demo-app"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


@pytest.fixture
def thread(client):
    project = project_with_repo(client, "Plugin shop")
    return client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()


def test_hook_commands_become_argument_lists_with_the_plugin_folder(tmp_path):
    argv = plugin_hooks.argv_of('node "${CLAUDE_PLUGIN_ROOT}/hooks/src/guard-bash.ts"', tmp_path / "my plugin", tmp_path)
    assert argv[0].lower().endswith(("node", "node.exe")) and Path(argv[1]) == tmp_path / "my plugin" / "hooks" / "src" / "guard-bash.ts"  # Windows: "C:\\…\\my plugin/hooks/…" is the same path
    assert {p.id for p, _ in plugin_hooks.matching("PreToolUse", "Bash")} == {"agentic-qe"}
    assert plugin_hooks.matching("PreToolUse", "file_access_write") == []  # matchers see Claude Code names only


def test_typed_gate_phrase_is_recorded_by_the_plugin_and_guard_bash_blocks_rm(client, thread):
    scripted = ScriptedClient([(NEEDLE, steps("Noted."))])
    llm.set_client_override(scripted)
    turn(client, thread["id"], f"approve gate 0 for {APP}", "r1")
    root = sandbox_dir(thread["project_id"])
    entries = [json.loads(line) for line in (root / ".qe" / "ledger.jsonl").read_text().splitlines()]
    assert [e["type"] for e in entries[:2]] == ["run_start", "gate_decision"]
    assert entries[1]["gate"] == 0 and entries[1]["decision"] == "APPROVED" and entries[1]["source"] == "user_prompt"
    assert json.loads((root / ".qe" / "run.json").read_text())["app"] == APP
    assert f"agentic-qe recorded: run started for {APP}; Gate 0 APPROVED" in scripted.calls[0]  # additionalContext reached the model
    events = [r for r in ledger_rows(thread["project_id"], "plugin.hook") if r["target"] == "UserPromptSubmit"]
    assert events and events[0]["actor"] == "plugin:agentic-qe" and events[0]["data"]["exit_code"] == 0

    scripted = ScriptedClient([(NEEDLE, steps({"call": "bash", "args": {"command": "rm -rf /"}}, "Blocked."))])  # hooks see it as Bash
    llm.set_client_override(scripted)
    approve(client, thread["id"], turn(client, thread["id"], "Clean everything", "r2"), "r3")
    assert "Blocked by a plugin hook before bash ran. Nothing ran." in scripted.calls[-1]
    assert "agentic-qe: deleting / is blocked (outside the project)" in scripted.calls[-1]  # guard-bash.ts's own reason
    blocked = [r for r in ledger_rows(thread["project_id"], "plugin.hook") if r["target"] == "PreToolUse"]
    assert blocked[-1]["data"]["blocked"] is True and blocked[-1]["data"]["tool"] == "Bash"
    assert ledger_rows(thread["project_id"], "harness.shell") == []


def test_a_message_that_is_not_a_phrase_records_nothing(client, thread):
    llm.set_client_override(ScriptedClient([(NEEDLE, steps("Hello."))]))
    turn(client, thread["id"], "please approve gate 0 for me", "r1")
    assert not (sandbox_dir(thread["project_id"]) / ".qe").exists()  # the whole message must be the phrase


def test_plugin_agents_are_read_only_background_agents(client, thread):
    llm.set_client_override(ScriptedClient([]))
    agent = harness.build(thread["project_id"], thread["id"], engine.start, user_id="admin")
    background = next(p for p in agent.context_providers if isinstance(p, BackgroundAgentsProvider))._agents
    plugin = {k: a for k, a in background.items() if k.startswith("agentic-qe:")}
    assert len(plugin) == 9 and "agentic-qe:coverage-auditor" in plugin and "test-design-architect" in background
    for child in plugin.values():
        access = [p for p in child.context_providers if isinstance(p, FileAccessProvider)]
        assert len(access) == 1 and access[0].disable_write_tools is True
        assert not [t for t in child.default_options.get("tools") or []]  # no shell or write tool of its own
    assert "Bash" in plugin["agentic-qe:defect-diagnostician"].description  # it says the harness keeps Write, Edit and Bash


def test_subagent_stop_runs_when_a_plugin_agent_finishes(client, thread):
    parent = steps({"call": "background_agents_start_task", "args": {"agent_name": "agentic-qe:coverage-auditor", "input": "Audit", "description": "audit"}},
                   {"call": "background_agents_wait_for_first_completion", "args": {"task_ids": [1]}}, "Audited.")
    llm.set_client_override(ScriptedClient([("You are the **Coverage Auditor**", steps("No cases to audit yet.")), (NEEDLE, parent)]))
    turn(client, thread["id"], "Audit coverage", "r1")
    stops = [r for r in ledger_rows(thread["project_id"], "plugin.hook") if r["target"] == "SubagentStop"]
    assert stops and stops[0]["data"]["exit_code"] == 0  # review-capture.ts ran; with no QE run it records nothing
