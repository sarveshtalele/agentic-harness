"""H9: a harness tool call produces a span with the same id as its tool_calls row, and a secret in its arguments never reaches a span.

The model is ScriptedClient; the AG-UI route, the harness, the tool_audit middleware, MAF's tool execution and the span store are real.
"""
from __future__ import annotations

import json

from backend.core import tracing
from backend.db import db, rows
from backend.maf import llm
from tests.scripted_client import ScriptedClient
from tests.test_maf_harness import NEEDLE, _tool_then_text, _turn, client, project  # noqa: F401 - fixtures

SECRET = "ghp_" + "Zq9Lw2Xe7R" * 4  # built at run time so no secret-shaped literal sits in the repository


def _trace_of_tool(project_id: str, tool: str) -> tuple[dict, list[dict]]:
    tracing.flush()
    with db() as con:
        call = dict(con.execute("SELECT * FROM tool_calls WHERE project_id=? AND tool=? ORDER BY id DESC LIMIT 1", (project_id, tool)).fetchone())
        spans = rows(con.execute("SELECT * FROM spans WHERE trace_id=?", (call["trace_id"],)))
    return call, spans


def test_a_tool_call_span_shares_the_id_of_its_tool_calls_row(client, project):
    llm.set_client_override(ScriptedClient([(NEEDLE, _tool_then_text("todos_add", {"todos": [{"title": "Read the BRD"}]}, "Added."))]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    _turn(client, thread["id"], "Make a plan", "m1")
    call, spans = _trace_of_tool(project["id"], "todos_add")
    assert call["span_id"] and call["trace_id"], "the tool_calls row must name the span that wrapped it"
    span = next(s for s in spans if s["span_id"] == call["span_id"])
    attributes = json.loads(span["attributes"])
    assert span["name"] == "tool todos_add" and attributes["tool_call_id"] == call["id"] and attributes["agent"] == "harness"
    root = next(s for s in spans if s["root"])
    assert root["name"] == "POST /agui/{agent_key}" and root["user_id"] == "admin"
    assert json.loads(root["attributes"])["project_id"] == project["id"]  # noted on the root by the call telemetry
    # MAF's own spans (agent run, model call, tool execution) sit in the same trace
    assert any(s["name"].startswith("execute_tool") for s in spans), [s["name"] for s in spans]
    trace = client.get(f"/api/traces/{call['trace_id']}").json()
    assert {s["span_id"] for s in trace["spans"]} == {s["span_id"] for s in spans}


def test_a_secret_in_a_tool_argument_never_reaches_a_stored_span(client, project):
    llm.set_client_override(ScriptedClient([(NEEDLE, _tool_then_text("todos_add", {"todos": [{"title": f"rotate {SECRET} today"}]}, "Added."))]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    _turn(client, thread["id"], "Track the token rotation", "m1")
    call, spans = _trace_of_tool(project["id"], "todos_add")
    assert len(spans) > 2
    tool_span = next(s for s in spans if s["span_id"] == call["span_id"])
    assert "rotate" in json.loads(tool_span["attributes"])["input"]  # the arguments are there, masked
    with db() as con:
        leaked = con.execute("SELECT COUNT(*) FROM spans WHERE instr(attributes, ?) > 0 OR instr(name, ?) > 0", (SECRET, SECRET)).fetchone()[0]
    assert leaked == 0
