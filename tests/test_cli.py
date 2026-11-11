"""The terminal harness is a client of the real AG-UI route: same harness, same sign-in, same audit."""
import io
import os

from fastapi.testclient import TestClient

from backend import cli
from backend.app import app
from backend.maf import llm
from tests.scripted_client import ScriptedClient

NEEDLE = "You are the Agentic QE Platform project harness"


def test_cli_turn_streams_the_harness_reply_and_names_each_tool(monkeypatch):
    calls = {"n": 0}

    def reply(_text):
        calls["n"] += 1
        return {"call": "todos_add", "args": {"todos": [{"title": "Read the code"}]}} if calls["n"] == 1 else "Planned one step."

    llm.set_client_override(ScriptedClient([(NEEDLE, reply)]))
    monkeypatch.setenv("ATLAS_CLI_USERNAME", "qa-admin")
    monkeypatch.setenv("ATLAS_CLI_PASSWORD", os.environ["ATLAS_ADMIN_PASSWORD"])
    try:
        with TestClient(app) as client:
            session = cli.Session("http://testserver")
            session.http = client
            session.sign_in()
            project = client.post("/api/projects", json={"name": "CLI shop", "description": "cli"}).json()["id"]
            thread = session.new_thread(project)
            out = io.StringIO()
            reply = session.turn(thread, "Plan one step", out)
            # execute mode: the open todo earns one more round; a round without a tool call ends the loop (harness_kit/nudges.py)
            assert reply.startswith("Planned one step.") and reply.count("Planned one step.") <= 2 and "open todo" not in reply
            assert "Using todos_add" in out.getvalue()
            assert [t["title"] for t in session.get(f"/api/chats/{thread}/todos")["todos"]] == ["Read the code"]
            assert client.get(f"/api/chats/{thread}").json()["messages"][-1]["content"].strip() == reply.strip()  # the stored reply is exactly what streamed
    finally:
        llm.set_client_override(None)


def test_cli_sign_in_failure_stops_with_the_reason(monkeypatch):
    monkeypatch.setenv("ATLAS_CLI_USERNAME", "nobody")
    monkeypatch.setenv("ATLAS_CLI_PASSWORD", "wrong-password-1")
    with TestClient(app) as client:
        session = cli.Session("http://testserver")
        session.http = client
        try:
            session.sign_in()
            raise AssertionError("sign-in should fail")
        except SystemExit as exc:
            assert "Sign-in failed (401)" in str(exc)
