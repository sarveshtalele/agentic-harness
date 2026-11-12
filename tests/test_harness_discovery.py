"""H1: the model sees every loadable tool by name and purpose from its first call, and one way to make a skill."""
import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.maf import llm
from tests.scripted_client import ScriptedClient

NEEDLE = "You are the Agentic QE Platform project harness"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


def test_first_call_lists_deferred_tools_by_name_and_hides_studio_skill(client):
    scripted = ScriptedClient([(NEEDLE, "Ready.")])
    llm.set_client_override(scripted)
    project = client.post("/api/projects", json={"name": "Discovery shop", "description": "H1"}).json()
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    body = {"threadId": thread["id"], "runId": "d1", "messages": [{"id": "d1", "role": "user", "content": "Start the qe workflow"}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/harness", json=body) as response:
        assert response.status_code == 200 and "Ready." in "".join(response.iter_text())
    first = scripted.calls[0]
    assert "Tools you can load with load_tools" in first
    for name in ("start_workflow", "create_skill", "run_tests", "save_document", "project_status"):
        assert f"- {name}(" in first, name  # since step 4 each name shows its arguments: name(a, b?)
    assert "- start_workflow(" in first and "Use when the user asks to run a workflow" in first
    assert "skill-creator" not in first  # one way to make a skill: the create_skill tool
