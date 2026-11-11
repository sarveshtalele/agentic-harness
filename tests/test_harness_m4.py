"""Plan M4 harness features on the real MAF stack, with only the model replaced by ScriptedClient: the web profile (D1),
progressive tool discovery, specialists as background agents, mode kept across requests, approval interrupts for risky
tools, the loop cap and compaction settings.
"""
from __future__ import annotations

import dataclasses
import json
import os

import pytest
from agent_framework import AgentLoopMiddleware, BackgroundAgentsProvider, SummarizationStrategy, TokenBudgetComposedStrategy, ToolResultCompactionStrategy
from fastapi.testclient import TestClient

from backend import config
from backend.app import app
from backend.db import db
from backend.maf import engine, governance, harness, llm
from tests.scripted_client import ScriptedClient

NEEDLE = "You are the Agentic QE Platform project harness"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


@pytest.fixture
def thread(client):
    project = client.post("/api/projects", json={"name": "M4 shop", "description": "harness M4"}).json()
    return client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()


def steps(*replies):
    """Model replies in order: a dict is a tool call, a string is the final text."""
    seen = {"n": 0}

    def reply(_text):
        seen["n"] += 1
        return replies[min(seen["n"], len(replies)) - 1]

    return reply


def turn(client, thread_id: str, text: str | None, run: str, resume=None) -> list[dict]:
    body = {"threadId": thread_id, "runId": run, "messages": [{"id": f"m_{run}", "role": "user", "content": text}] if text else [],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    if resume:
        body["resume"] = resume
    with client.stream("POST", "/agui/harness", json=body) as response:
        assert response.status_code == 200
        raw = "".join(response.iter_text())
    return [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]


def tool_rows(project_id: str, agent: str = "harness") -> list[dict]:
    with db() as con:
        return [dict(r) for r in con.execute("SELECT tool, status, error FROM tool_calls WHERE project_id=? AND agent=? ORDER BY id", (project_id, agent))]


def test_web_profile_runs_the_harness_too(client, thread, monkeypatch):
    """Decision D1 (plan H2): the harness runs on the web profile; its writes and commands share the sandbox slots."""
    monkeypatch.setattr(config, "PROFILE", "web")
    assert client.get("/api/profile").json() == {"profile": "web"}
    llm.set_client_override(ScriptedClient([(NEEDLE, "Hello from the web profile.")]))
    events = turn(client, thread["id"], "hello", "web1")
    assert events[-1]["type"] == "RUN_FINISHED" and any(e.get("delta") == "Hello from the web profile." for e in events)
    assert client.get(f"/api/chats/{thread['id']}/todos").status_code == 200
    monkeypatch.setattr(config, "PROFILE", "local")


def test_find_and_load_tools_load_only_allowed_tools_and_keep_them(client, thread, monkeypatch):
    policy = governance.POLICIES["harness"]
    monkeypatch.setitem(governance.POLICIES, "harness", dataclasses.replace(policy, chat_tools=policy.chat_tools - {"verify_ledger"}))
    scripted = ScriptedClient([(NEEDLE, steps({"call": "find_tools", "args": {"query": "project status ledger"}},
                                             {"call": "load_tools", "args": {"names": ["project_status", "verify_ledger"]}},
                                             {"call": "project_status", "args": {}}, "Status read."))])
    llm.set_client_override(scripted)
    turn(client, thread["id"], "How is the project?", "r1")
    assert '"name": "project_status"' in scripted.calls[1] and "verify_ledger" not in scripted.calls[1]  # catalogue holds allowed tools only
    loaded = scripted.calls[2]
    assert '"loaded": ["project_status"]' in loaded and '"verify_ledger": "not a tool this harness may load' in loaded
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "project_status", "args": {}}, "Again."))]))
    turn(client, thread["id"], "And now?", "r2")  # a new request: the loaded tool comes back from the thread's store
    rows = tool_rows(thread["project_id"])
    assert [r["tool"] for r in rows] == ["find_tools", "load_tools", "project_status", "project_status"]
    assert all(r["status"] == "ok" for r in rows)
    stored = harness.HARNESS_DIR / thread["project_id"] / "tools" / f"{thread['id']}.json"
    assert json.loads(stored.read_text()) == ["project_status"]


def test_specialist_runs_as_a_background_agent_and_its_tool_call_is_audited(client, thread):
    parent = steps({"call": "background_agents_start_task", "args": {"agent_name": "requirements-analyst", "input": "List the files", "description": "files"}},
                   {"call": "background_agents_wait_for_first_completion", "args": {"task_ids": [1]}}, "Delegated.")
    scripted = ScriptedClient([("You are a requirements analyst", steps({"call": "list_files", "args": {}}, "Found the files.")), (NEEDLE, parent)])
    llm.set_client_override(scripted)
    events = turn(client, thread["id"], "Ask the requirements analyst", "r1")
    started = [e for e in events if e["type"] == "TOOL_CALL_START"]
    assert started[0]["toolCallName"] == "background_agents_start_task"
    assert "requirements-analyst" in scripted.calls[0] and "Derives testable requirements" in scripted.calls[0]  # the governed list
    assert [r["tool"] for r in tool_rows(thread["project_id"], "requirements-analyst")] == ["list_files"]
    assert "background_agents_start_task" in [r["tool"] for r in tool_rows(thread["project_id"])]


def test_execute_mode_persists_across_requests(client, thread):
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "mode_set", "args": {"mode": "execute"}}, "Executing."))]))
    turn(client, thread["id"], "Go ahead", "r1")
    scripted = ScriptedClient([(NEEDLE, steps({"call": "mode_get", "args": {}}, "Still executing."))])
    llm.set_client_override(scripted)
    turn(client, thread["id"], "Which mode?", "r2")
    assert "currently operating in the execute mode" in scripted.calls[0]  # MAF's mode instructions on the new request
    with db() as con:  # the mode lives in the durable thread snapshot, not in process memory
        body = con.execute("SELECT body FROM harness_snapshots WHERE thread_id=?", (thread["id"],)).fetchone()["body"]
    assert '"current_mode": "execute"' in body


def test_risky_tool_waits_for_approval_and_runs_only_after_it(client, thread):
    fact = "fact-" + os.urandom(4).hex()
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "load_tools", "args": {"names": ["remember"]}}, {"call": "remember", "args": {"fact": fact}}, "Remembered."))]))
    events = turn(client, thread["id"], "Remember this", "r1")
    finished = events[-1]
    assert finished["type"] == "RUN_FINISHED" and finished["outcome"]["type"] == "interrupt"
    interrupt = finished["outcome"]["interrupts"][0]
    assert interrupt["reason"] == "tool_call" and "remember" in interrupt["message"]
    memories = lambda: client.get(f"/api/projects/{thread['project_id']}/memories").json()  # noqa: E731
    assert memories() == []  # nothing ran before a human answered
    events = turn(client, thread["id"], None, "r2", resume=[{"interruptId": interrupt["id"], "status": "resolved", "payload": {"approved": True}}])
    assert any(e["type"] == "TOOL_CALL_RESULT" for e in events)
    assert [m["content"] for m in memories()] == [fact]
    assert "remember" in [r["tool"] for r in tool_rows(thread["project_id"])]


def test_loop_cap_compaction_and_background_agents_are_configured(client, thread):
    llm.set_client_override(ScriptedClient([]))
    agent = harness.build(thread["project_id"], thread["id"], engine.start, user_id="admin")
    loop = next(m for m in agent.middleware if isinstance(m, AgentLoopMiddleware))
    assert loop.max_iterations == config.HARNESS_MAX_ROUNDS != 10
    strategy = agent.compaction_strategy
    assert isinstance(strategy, TokenBudgetComposedStrategy)
    assert [type(s) for s in strategy.strategies] == [ToolResultCompactionStrategy, SummarizationStrategy]
    assert strategy.token_budget == config.HARNESS_CONTEXT_TOKENS - governance.token_limit("harness")
    background = next(p for p in agent.context_providers if isinstance(p, BackgroundAgentsProvider))
    assert set(background._agents) >= {"test-design-architect", "requirements-analyst", "repo-intelligence-analyst", "principal-test-architect"}
    names = [t.name for t in agent.default_options["tools"]]
    assert {"find_tools", "load_tools", "read_file", "grep"} <= set(names) and "run_tests" not in names  # a small core


def test_rejected_risky_tool_never_runs(client, thread):
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "load_tools", "args": {"names": ["remember"]}}, {"call": "remember", "args": {"fact": "no"}}, "Not saved."))]))
    interrupt = turn(client, thread["id"], "Remember this", "r1")[-1]["outcome"]["interrupts"][0]
    turn(client, thread["id"], None, "r2", resume=[{"interruptId": interrupt["id"], "status": "resolved", "payload": {"approved": False}}])
    assert client.get(f"/api/projects/{thread['project_id']}/memories").json() == []


def test_loop_nudges_never_reach_the_reply_and_a_round_without_tools_ends_the_loop(client, thread):
    calls = {"n": 0}

    def reply(_text):
        calls["n"] += 1
        return {"call": "todos_add", "args": {"todos": [{"title": "Read the code"}]}} if calls["n"] == 1 else "Working on it."

    llm.set_client_override(ScriptedClient([(NEEDLE, reply)]))
    turn(client, thread["id"], "Plan one step", "loop1")
    stored = client.get(f"/api/chats/{thread['id']}").json()["messages"][-1]["content"]
    assert "Progress so far" not in stored and "open todo" not in stored  # MAF's injected user prompts stay out of the reply
    assert calls["n"] <= 3 and stored.count("Working on it.") == 2  # one extra round for the open todo, then the text-only round stops it
