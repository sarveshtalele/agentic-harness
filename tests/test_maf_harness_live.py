"""Live: the project harness on the real model (plan P2). Run with  pytest -m live tests/test_maf_harness_live.py
with OPENAI_BASE_URL, OPENAI_API_KEY and DEFAULT_MODEL set. A missing model is a failure, not a skip.
"""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.db import db
from backend.maf import harness

pytestmark = pytest.mark.live


def test_harness_plans_with_todos_and_a_skill_on_the_real_model():
    assert os.environ.get("DEFAULT_MODEL") and os.environ.get("OPENAI_API_KEY"), "live test needs a real model in the environment"
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        project = client.post("/api/projects", json={"name": "Live harness", "description": "Login page for a banking app"}).json()
        thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
        prompt = ("Load the planning-tests skill, then add exactly two todos for planning the tests of a login page, "
                  "then reply with the two todo titles.")
        body = {"threadId": thread["id"], "runId": "live1", "messages": [{"id": "m1", "role": "user", "content": prompt}],
                "state": {}, "tools": [], "context": [], "forwardedProps": {}}
        with client.stream("POST", "/agui/harness", json=body, timeout=300) as response:
            stream = "".join(response.iter_text())
    assert "RUN_FINISHED" in stream and "RUN_ERROR" not in stream, stream[-800:]
    with db() as con:
        used = [r["tool"] for r in con.execute("SELECT tool FROM tool_calls WHERE project_id=? AND agent='harness' ORDER BY id", (project["id"],))]
        calls = con.execute("SELECT COUNT(*) FROM agent_calls WHERE project_id=? AND agent='harness'", (project["id"],)).fetchone()[0]
    print("LIVE tools used:", json.dumps(used), "model calls:", calls)
    assert calls >= 1, "telemetry must record the real model call"
    assert "load_skill" in used and "todos_add" in used, f"the model did not use the harness tools it was asked to: {used}"
    todos = "".join(p.read_text(encoding="utf-8") for p in (harness.HARNESS_DIR / project["id"] / "todos").rglob("*.json"))
    assert todos.count('"title"') >= 2, todos[:500]
