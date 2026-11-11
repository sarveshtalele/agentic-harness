"""BA workflow gates and the bug scan through the real API."""

import json

from backend.maf import llm

from tests.scripted_client import ScriptedClient
from tests.helpers_api import BUGGY, client, GOOD_REVIEW, pending, project, rules, upload_repo, wait_run  # noqa: F401 - fixtures


def test_ba_workflow_pauses_resumes_rejects_and_approves(client, project):
    llm.set_client_override(ScriptedClient(rules()))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "ba", "input": {"brief": "Password reset link that expires in 30 minutes", "template_id": "builtin_brd", "title": "Reset BRD"}}).json()
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval", run["error"]
    gate0 = pending(run)
    assert gate0["gate"] == 0

    assert client.post(f"/api/approvals/{gate0['id']}/decide", json={"approved": True, "by": "someone else"}).status_code == 200
    assert client.get(f"/api/projects/{project['id']}/gates").json()[0]["decided_by"] == "admin", "a typed signer is ignored"
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval", run["error"]
    gate1 = pending(run)
    assert gate1["gate"] == 1
    doc_id, feature_id = gate1["payload"]["documents"]
    assert client.get(f"/api/documents/{feature_id}").json()["gherkin"]["valid"]

    client.post(f"/api/approvals/{gate1['id']}/decide", json={"approved": False, "feedback": "Add lockout rule"})
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval", run["error"]
    second = pending(run)
    assert second["id"] != gate1["id"]
    assert client.get(f"/api/documents/{doc_id}").json()["note"].startswith("Revision: Add lockout")

    client.post(f"/api/approvals/{second['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"], ("completed", "failed"))
    assert run["status"] == "completed", run["error"]
    assert client.get(f"/api/documents/{doc_id}").json()["status"] == "approved"
    gates = {g["gate"]: g for g in client.get(f"/api/projects/{project['id']}/gates").json()}
    assert gates[1]["status"] == "approved" and gates[1]["decided_by"] == "admin" and gates[1]["signature_valid"]
    assert client.post(f"/api/approvals/{second['id']}/decide", json={"approved": True}).status_code == 400
    assert client.get(f"/api/projects/{project['id']}/ledger").json()["verification"]["valid"]
    assert client.get(f"/api/documents/{doc_id}").json()["prompt_ref"].startswith("business-analyst@v")


def test_ba_loops_on_low_review_score(client, project):
    scores = iter(['{"score": 40, "verdict": "REVISE", "issues": ["Scope is vague"]}', GOOD_REVIEW])
    scripted = [("Review type: requirements document", lambda _: next(scores)), *rules()[1:]]
    llm.set_client_override(ScriptedClient(scripted))
    project_id = project["id"]
    run = wait_run(client, client.post(f"/api/projects/{project_id}/runs", json={"workflow": "ba", "input": {"brief": "x"}}).json()["id"])
    client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval", run["error"]
    doc = client.get(f"/api/documents/{pending(run)['payload']['documents'][0]}").json()
    assert doc["version"] == 2 and "Scope is vague" in doc["note"]


def test_ba_requires_input(client, project):
    llm.set_client_override(ScriptedClient(rules()))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "ba", "input": {"brief": "  "}}).json()["id"])
    client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"], ("failed", "completed"))
    assert run["status"] == "failed" and "brief" in run["error"]


def test_unknown_workflow_rejected(client, project):
    llm.set_client_override(ScriptedClient(rules()))
    assert client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "nope"}).status_code == 400


def test_bug_scan_keeps_verified_and_drops_hallucinated_findings(client, project):
    upload_repo(client, project, BUGGY)
    review = json.dumps({"findings": [
        {"title": "Division by zero", "severity": "high", "file": "app/core.py", "line": 9, "quote": "return a / b", "explanation": "b=0 raises"},
        {"title": "Invented", "severity": "critical", "file": "app/core.py", "line": 3, "quote": "os.system(user_input)", "explanation": "not real"},
        {"title": "Escape", "severity": "critical", "file": "../../etc/passwd", "line": 1, "quote": "root", "explanation": "nope"},
    ]})
    llm.set_client_override(ScriptedClient([("You review code for real defects", review)]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"}).json()["id"], ("completed", "failed"))
    assert run["status"] == "completed", run["error"]
    assert run["state"]["agent_verified"] == 1 and run["state"]["agent_rejected"] == 2
    findings = client.get(f"/api/projects/{project['id']}/findings").json()
    titles = [f["title"] for f in findings]
    assert "Division by zero" in titles and "Invented" not in titles
    assert any(f["source"] == "ruff" and "shell=True" in f["evidence"] for f in findings)
    agent = next(f for f in findings if f["source"] == "agent")
    assert agent["line"] == 9

    dismissed = client.patch(f"/api/findings/{agent['id']}", json={"status": "dismissed"}).json()
    assert dismissed["status"] == "dismissed" and agent["id"] not in [f["id"] for f in client.get(f"/api/projects/{project['id']}/findings").json()]


def test_rescan_does_not_duplicate_findings(client, project):
    upload_repo(client, project, BUGGY)
    llm.set_client_override(ScriptedClient([("You review code for real defects", '{"findings": []}')]))
    for _ in range(2):
        wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"}).json()["id"], ("completed", "failed"))
    findings = client.get(f"/api/projects/{project['id']}/findings").json()
    assert len(findings) == len({(f["rule"], f["file"], f["line"]) for f in findings})
