"""H9: a background workflow run is its own trace, with a span per stage and the run's project, user and tokens on its root."""
from __future__ import annotations

import json

from backend.core import tracing
from backend.db import db, rows
from backend.maf import llm
from tests.helpers_api import client, pending, project, rules, wait_run  # noqa: F401 - fixtures
from tests.scripted_client import ScriptedClient


def test_a_workflow_run_is_one_trace_with_a_span_per_stage(client, project):
    llm.set_client_override(ScriptedClient(rules()))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "ba", "input": {"brief": "Password reset link that expires in 30 minutes", "template_id": "builtin_brd", "title": "Reset BRD"}}).json()
    gate0 = pending(wait_run(client, run["id"]))
    assert client.post(f"/api/approvals/{gate0['id']}/decide", json={"approved": True}).status_code == 200
    assert wait_run(client, run["id"])["status"] == "waiting_approval"  # the resumed segment drafts the BRD on the model
    tracing.flush()
    with db() as con:
        roots = rows(con.execute("SELECT * FROM spans WHERE root=1 AND name='workflow ba' AND json_extract(attributes,'$.run_id')=? ORDER BY started_at", (run["id"],)))
        assert len(roots) == 2, "the start and the resume are one trace each"
        root = roots[-1]
        spans = rows(con.execute("SELECT name, parent_id FROM spans WHERE trace_id=?", (root["trace_id"],)))
    attributes = json.loads(root["attributes"])
    assert root["project_id"] == project["id"] and root["user_id"] == "admin"
    assert attributes["tokens_in"] > 0 and attributes["agent"]  # noted by the call telemetry of the stage's agent
    assert any(s["name"].startswith("stage ") for s in spans), [s["name"] for s in spans]
    listed = client.get("/api/traces", params={"project": project["id"]}).json()["items"]
    assert root["trace_id"] in {item["trace_id"] for item in listed}
