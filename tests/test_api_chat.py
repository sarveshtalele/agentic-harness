"""AG-UI chat, memory, prompts, repository endpoints and manual gates."""

import json

from backend.maf import llm
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import CASES, client, GOOD_REVIEW, pending, PLAN, project, REQUIREMENTS, upload_repo, wait_run  # noqa: F401 - fixtures


def test_agui_chat_streams_persists_and_scopes_to_thread(client, project):
    llm.set_client_override(ScriptedClient([("You are the Agentic QE Platform project copilot", "Hello from the copilot")]))
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot"}).json()
    body = {"threadId": thread["id"], "runId": "r1", "messages": [{"id": "m1", "role": "user", "content": "Say hello please"}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/project-copilot", json=body) as response:
        text = "".join(response.iter_text())
    assert "RUN_STARTED" in text and "Hello from the copilot" in text and "RUN_FINISHED" in text
    saved = client.get(f"/api/chats/{thread['id']}").json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["title"] == "Say hello please" and saved["messages"][1]["content"] == "Hello from the copilot"
    assert client.post("/agui/project-copilot", json={**body, "threadId": "thr_unknown"}).status_code == 404


def test_memory_appears_in_agent_context(client, project):
    scripted = ScriptedClient([("You are the Agentic QE Platform project copilot", "ok")])
    llm.set_client_override(scripted)
    client.post(f"/api/projects/{project['id']}/memories", json={"content": "Release freeze starts Friday"})
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot"}).json()
    body = {"threadId": thread["id"], "runId": "r1", "messages": [{"id": "m1", "role": "user", "content": "hi"}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/project-copilot", json=body) as response:
        "".join(response.iter_text())
    assert any("Release freeze starts Friday" in call for call in scripted.calls)


def test_prompt_edit_is_used_by_next_run(client, project):
    scripted = ScriptedClient([("BRAND NEW PROMPT TEXT", '{"findings": []}')])
    llm.set_client_override(scripted)
    upload_repo(client, project, {"m.py": "x = 1\n"})
    original = client.get("/api/prompts/bug-reviewer").json()[0]
    created = client.post("/api/prompts/bug-reviewer", json={"body": "BRAND NEW PROMPT TEXT for review", "note": "test"}).json()
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"}).json()["id"], ("completed", "failed"))
    assert run["status"] == "completed", run["error"]
    assert client.post(f"/api/prompts/bug-reviewer/activate/{original['version']}").json()["version"] == original["version"]
    assert created["version"] == original["version"] + 1


def test_repo_file_endpoint_blocks_traversal(client, project):
    upload_repo(client, project, {"a.py": "x=1\n"})
    assert client.get(f"/api/projects/{project['id']}/repo/file", params={"path": "a.py"}).text == "x=1\n"
    assert client.get(f"/api/projects/{project['id']}/repo/file", params={"path": "../../../.secret.key"}).status_code >= 400


def test_zip_cannot_resync(client, project):
    upload_repo(client, project, {"a.py": "x=1\n"})
    response = client.post(f"/api/projects/{project['id']}/repo/resync")
    assert response.status_code == 400 and "ZIP" in response.json()["detail"]


def test_git_file_url_rejected_by_api(client, project):
    response = client.post(f"/api/projects/{project['id']}/repo/git", json={"url": "file:///etc"})
    assert response.status_code == 400 and "https" in response.json()["detail"]


def test_generated_tests_with_placeholders_are_refused(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    placeholder = json.dumps({"framework": "pytest", "files": [{"path": "tests/agentic_qe/test_x.py", "case_ids": ["TC-APP-001"], "content": "# CASE_ID: TC-APP-001\ndef test_x():\n    pass\n"}]})
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", REQUIREMENTS), ("You are a principal test architect", PLAN),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'), ("You are a test design architect", CASES), ("You are a test automation engineer", placeholder),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(4):
        run = wait_run(client, run["id"])
        if run["status"] != "waiting_approval":
            break
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"], ("failed", "completed"))
    assert run["status"] == "failed" and "placeholder" in run["error"]


def test_local_folder_import_and_shorthand(client, project, tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.js").write_text("x")
    result = client.post(f"/api/projects/{project['id']}/repo/local", json={"path": str(tmp_path)}).json()
    assert result["kind"] == "local" and result["analysis"]["total_files"] == 1
    assert (tmp_path / ".git").exists() is False, "the original folder stays untouched"
    assert client.post(f"/api/projects/{project['id']}/repo/local", json={"path": str(tmp_path / "none")}).status_code == 400


def test_document_review_and_refine(client, project):
    llm.set_client_override(ScriptedClient([("Review type: requirements document", GOOD_REVIEW), ("Artifact: requirements document", "## Scope\nRefined")]))
    doc = client.post(f"/api/projects/{project['id']}/documents", json={"title": "D", "kind": "brd", "content": "## Scope\nOld"}).json()
    assert client.post(f"/api/documents/{doc['id']}/review").json()["score"] == 90
    refined = client.post(f"/api/documents/{doc['id']}/refine", json={"instructions": "tighten"}).json()
    assert refined["version"] == 2 and refined["content"] == "## Scope\nRefined" and refined["prompt_ref"].startswith("business-analyst@v")


def test_manual_gate_decision_keeps_order(client, project):
    assert client.post(f"/api/projects/{project['id']}/gates/2/decision", json={"approved": True}).status_code == 400
    state = client.post(f"/api/projects/{project['id']}/gates/0/decision", json={"approved": True, "reason": "Scope agreed"}).json()
    assert state[0]["status"] == "approved" and state[0]["reason"] == "Scope agreed"
