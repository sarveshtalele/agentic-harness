"""The project harness (plan P2): MAF's create_harness_agent behind the existing AG-UI route, with the model replaced
only by ScriptedClient. Checks progressive skill disclosure, a real load_skill call, todos that persist per thread,
every tool call recorded (CI gate 3), and per-call history kept on disk (CI gate 2, model-visible means logged).
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.db import db
from backend.maf import harness, llm
from tests.scripted_client import ScriptedClient

NEEDLE = "You are the Agentic QE Platform project harness"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


@pytest.fixture
def project(client):
    return client.post("/api/projects", json={"name": "Harness shop", "description": "P2 tests"}).json()


def _turn(client, thread_id: str, text: str, msg_id: str) -> str:
    body = {"threadId": thread_id, "runId": f"r_{msg_id}", "messages": [{"id": msg_id, "role": "user", "content": text}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/harness", json=body) as response:
        assert response.status_code == 200
        return "".join(response.iter_text())


def _tool_then_text(call: str, args: dict, final: str):
    """First model call asks for one tool; the call after the tool result answers in text."""
    seen = {"n": 0}

    def reply(_text):
        seen["n"] += 1
        return {"call": call, "args": args} if seen["n"] == 1 else final

    return reply


def test_harness_streams_and_offers_skills_by_name_only(client, project):
    scripted = ScriptedClient([(NEEDLE, "Plan ready.")])
    llm.set_client_override(scripted)
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    text = _turn(client, thread["id"], "Plan the test strategy", "m1")
    assert "RUN_STARTED" in text and "Plan ready." in text and "RUN_FINISHED" in text
    first = scripted.calls[0]
    assert "planning-tests" in first and "decomposing requirements across Unit" in first  # name and description advertised
    saved = client.get(f"/api/chats/{thread['id']}").json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]


def test_load_skill_returns_the_real_skill_body_and_is_recorded(client, project):
    skill_text = (harness.SKILLS_DIR / "planning-tests" / "SKILL.md").read_text(encoding="utf-8")
    body_marker = next(line for line in skill_text.split("---", 2)[2].splitlines() if line.strip().startswith("#"))
    scripted = ScriptedClient([(NEEDLE, _tool_then_text("load_skill", {"skill_name": "planning-tests"}, "Loaded."))])
    llm.set_client_override(scripted)
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    _turn(client, thread["id"], "Use the planning skill", "m1")
    assert body_marker not in scripted.calls[0]  # progressive disclosure: the body is not in the first request
    assert body_marker in scripted.calls[1]  # it arrives only as the load_skill result
    with db() as con:
        names = [r["tool"] for r in con.execute("SELECT tool FROM tool_calls WHERE project_id=? AND agent='harness'", (project["id"],))]
    assert "load_skill" in names  # CI gate 3: every tool call leaves a tool_calls row


def test_todos_persist_across_turns_of_one_thread(client, project):
    llm.set_client_override(ScriptedClient([(NEEDLE, _tool_then_text("todos_add", {"todos": [{"title": "Read the BRD"}]}, "Added."))]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    _turn(client, thread["id"], "Make a plan", "m1")
    scripted = ScriptedClient([(NEEDLE, _tool_then_text("todos_get_all", {}, "Listed."))])
    llm.set_client_override(scripted)
    _turn(client, thread["id"], "What is on the list?", "m2")
    assert "Read the BRD" in scripted.calls[1]  # the second turn's tool result reads the stored todo
    with db() as con:  # MAF's own harness tools are allowed for this agent, so none is logged as refused
        refused = con.execute("SELECT COUNT(*) FROM tool_calls WHERE project_id=? AND error LIKE 'Refused%'", (project["id"],)).fetchone()[0]
    assert refused == 0
    stored = list((harness.HARNESS_DIR / project["id"] / "todos").rglob("*.json"))
    assert stored, "todos must be on disk under data/harness, not in process memory"


def test_every_model_call_is_kept_in_history_on_disk(client, project):
    llm.set_client_override(ScriptedClient([(NEEDLE, "Noted.")]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    _turn(client, thread["id"], "Remember the release is in May", "m1")
    files = list((harness.HARNESS_DIR / project["id"] / "history").rglob("*"))
    text = "".join(f.read_text(encoding="utf-8", errors="replace") for f in files if f.is_file())
    assert "Remember the release is in May" in text and "Noted." in text  # CI gate 2: what the model saw and said
    with db() as con:  # telemetry records each streamed model round, inside the harness too
        rounds = con.execute("SELECT COUNT(*) FROM agent_calls WHERE project_id=? AND agent='harness' AND status='ok'", (project["id"],)).fetchone()[0]
    assert rounds == 1


def test_harness_state_never_lands_in_the_process_cwd(client, project, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    llm.set_client_override(ScriptedClient([(NEEDLE, "ok")]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    _turn(client, thread["id"], "hello", "m1")
    assert not (tmp_path / "agent-file-memory").exists()


def test_tool_call_written_as_text_ends_the_turn_with_an_error(client, project):
    """Live E2E caught the model replying with its tool-call syntax as text; the chat must not show or store it."""
    markup = 'Let me check.<｜DSML｜tool_calls> <｜DSML｜invoke name="list_files"> </｜DSML｜invoke> </｜DSML｜tool_calls>'
    llm.set_client_override(ScriptedClient([("You are the Agentic QE Platform project copilot", markup)]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot"}).json()
    body = {"threadId": thread["id"], "runId": "r1", "messages": [{"id": "m1", "role": "user", "content": "hi"}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/project-copilot", json=body) as response:
        text = "".join(response.iter_text())
    assert "DSML" not in text and "AQE-MODEL-TOOL-TEXT" in text and "RUN_FINISHED" not in text
    saved = client.get(f"/api/chats/{thread['id']}").json()["messages"]
    assert saved[-1]["role"] == "assistant" and saved[-1]["content"] == "Let me check."
