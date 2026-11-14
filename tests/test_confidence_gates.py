"""Test-file review and gate reopening after edits."""

import json

import pytest

from backend.core import documents, gates, ledger

from tests.helpers_api import TESTS, client, pending, project, wait_run  # noqa: F401 - fixtures
from tests.helpers_confidence import base_rules, go_to_gate


def test_generated_tests_are_reviewed_per_file_and_brownfield_does_not_cap_them_because_nothing_runs(client, project):
    failing = json.loads(TESTS)
    failing["files"][1]["content"] = failing["files"][1]["content"].replace("== 0", "== 5")  # TC-APP-002 asserts a wrong value, so it fails when run
    ninety_five = lambda kind, key: {"scores": {"import_safety": 15}} if kind == "code" else None
    seen = []
    rules = base_rules(grade=ninety_five, seen=seen)
    rules = [r if r[0] != "You are a test automation engineer" else (r[0], json.dumps(failing)) for r in rules]
    run, _ = go_to_gate(client, project, 4, rules)
    review = pending(run)["payload"]["confidence"]
    assert [r["tc_id"] for r in review["records"]] == ["TC-APP-001", "TC-APP-002", "TC-APP-003", "TC-APP-004"] and review["score"] == 95
    assert [s for s in seen if s[0] == "code"][0][1] == ["TC-APP-001", "TC-APP-002", "TC-APP-003", "TC-APP-004"]
    assert all(r["file"].startswith("tests/agentic_qe/") and r["evidence"] == "verified" for r in review["records"])
    assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True}).status_code == 200
    run = wait_run(client, run["id"])
    gate = pending(run)
    assert gate["gate"] == 5
    after = gate["payload"]["confidence"]
    assert gate["payload"]["summary"]["verdict"] == "NOT EXECUTED"
    assert after["score"] == 95, "nothing ran, so nothing is capped"
    assert all(not r.get("capped") and r["total"] == 95 for r in after["records"])
    assert run["state"]["tests_review"]["score"] == 95 and run["state"]["tests_review_after"]["score"] == 95
    assert client.post(f"/api/approvals/{gate['id']}/decide", json={"approved": True}).status_code == 200, "no failed test is a REJECT item: brownfield tests are not executed here"


def test_a_rejected_test_file_goes_back_alone_and_is_rewritten_on_the_branch(client, project):
    state = {"first": True}

    def grade(kind, key):
        if kind == "code" and key == "TC-APP-003" and state["first"]:
            state["first"] = False
            return {"scores": {"assertion_integrity": 0, "compilable": 10, "import_safety": 10, "traceability_present": 10}, "flaws": [{"dimension": "assertion_integrity", "evidence": "tests/agentic_qe/test_tc_app_003.py:5", "fix": "Assert the sum"}]}
        return None

    rewrites = []
    better = json.loads(TESTS)["files"][2]
    better["content"] = better["content"].replace("assert add(0, 0) == 0", "assert add(0, 0) + 1 == 1")

    def rewrite(text):
        rewrites.append(text)
        return json.dumps({"framework": "pytest", "files": [better]})

    run, _ = go_to_gate(client, project, 4, base_rules(grade=grade, extra=[("Rewrite only this generated test file", rewrite)]))
    assert len(rewrites) == 1 and "test_tc_app_003.py" in rewrites[0] and "Assert the sum" in rewrites[0]
    sent = rewrites[0].rsplit("Rewrite only this generated test file", 1)[-1]
    assert "TC-APP-001" not in sent and "TC-APP-004" not in sent, "no other case is sent"
    record = next(r for r in pending(run)["payload"]["confidence"]["records"] if r["tc_id"] == "TC-APP-003")
    assert record["round"] == 2 and record["verdict"] == "APPROVED"
    from backend.config import project_dir

    written = next((project_dir(project["id"]) / "worktrees").glob("*/tests/agentic_qe/test_tc_app_003.py")).read_text(encoding="utf-8")
    assert "+ 1 == 1" in written


# gate reopening


def approve_all_gates(project_id):
    for number in range(6):
        gates.decide(project_id, number, True, "usr_qa", "agreed")


def test_editing_approved_requirements_reopens_g1_to_g5_and_the_ledger_still_verifies(client, project):
    pid = project["id"]
    req = documents.create(pid, "requirements", "Requirements", "| ID |\n|---|\n| REQ-001 |", "usr_qa")
    plan = documents.create(pid, "test_plan", "Plan", "plan", "usr_qa")
    approve_all_gates(pid)
    assert [g["status"] for g in gates.status(pid)] == ["approved"] * 6
    page = client.get(f"/api/documents/{req['id']}").json()
    assert page["would_reopen"] == [1, 2, 3, 4, 5], "the page can warn before saving"
    saved = client.put(f"/api/documents/{req['id']}", json={"content": "| ID |\n|---|\n| REQ-001 |\n| REQ-002 |", "note": "Added"})
    assert saved.status_code == 200 and saved.json()["reopened"] == [1, 2, 3, 4, 5]
    after = gates.status(pid)
    assert after[0]["status"] == "approved" and all(g["status"] == "pending" and g["decided_by"] is None for g in after[1:])
    reopened = [e for e in ledger.entries(pid) if e["action"] == "gate.reopened"]
    assert sorted(e["target"] for e in reopened) == ["G1", "G2", "G3", "G4", "G5"]
    detail = json.loads(next(e for e in reopened if e["target"] == "G1")["data"])
    assert detail["cause"].startswith("requirements edited") and detail["document"] == req["id"] and detail["was"] == "approved" and detail["decided_by"] == "usr_qa" and detail["signature"]
    assert ledger.verify(pid)["valid"] is True
    assert client.get(f"/api/documents/{plan['id']}").json()["would_reopen"] == [], "nothing is approved now, so nothing would reopen"


def test_a_later_gate_cannot_be_approved_while_an_earlier_one_is_open(client, project):
    pid = project["id"]
    req = documents.create(pid, "requirements", "Requirements", "one", "usr_qa")
    approve_all_gates(pid)
    documents.save_version(req["id"], "two", "usr_qa")
    with pytest.raises(gates.GateOrderError, match="Gate 1 must be approved before gate 2"):
        gates.decide(pid, 2, True, "usr_qa", "again")
    assert client.post(f"/api/projects/{pid}/gates/2/decision", json={"approved": True}).status_code == 400
    gates.decide(pid, 1, True, "usr_qa", "re-approved")
    gates.decide(pid, 2, True, "usr_qa", "re-approved")
    assert [g["status"] for g in gates.status(pid)][:3] == ["approved"] * 3 and ledger.verify(pid)["valid"] is True


def test_a_run_waiting_on_a_reopened_gate_cannot_be_approved_past_it(client, project):
    run, _ = go_to_gate(client, project, 2, base_rules())
    req = next(d for d in client.get(f"/api/projects/{project['id']}/documents").json() if d["kind"] == "requirements")
    saved = client.put(f"/api/documents/{req['id']}", json={"content": "# Changed\n\nREQ-001 now differs", "note": "Edited"}).json()
    assert saved["reopened"] == [1]
    refused = client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    assert refused.status_code == 400 and "Gate 1 must be approved before gate 2" in refused.text
    assert client.get(f"/api/runs/{run['id']}").json()["status"] == "waiting_approval", "the run stays waiting, honestly"
    assert client.post(f"/api/projects/{project['id']}/gates/1/decision", json={"approved": True, "reason": "Edit reviewed"}).status_code == 200
    assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True}).status_code == 200


def test_restoring_an_old_version_also_reopens_but_a_first_version_and_a_draft_do_not(client, project):
    pid = project["id"]
    created = documents.create(pid, "requirements", "Requirements", "v1", "usr_qa")
    assert created["reopened"] == [], "a new document is not an edit"
    for number in range(6):
        gates.decide(pid, number, True, "usr_qa", "ok")
    documents.save_version(created["id"], "v2", "usr_qa")
    assert [g["status"] for g in gates.status(pid)][1:] == ["pending"] * 5
    for number in range(1, 6):
        gates.decide(pid, number, True, "usr_qa", "ok")
    restored = client.post(f"/api/documents/{created['id']}/restore/1")
    assert restored.status_code == 200 and restored.json()["reopened"] == [1, 2, 3, 4, 5]
    other = documents.create(pid, "brd", "Business doc", "x", "usr_qa")
    for number in range(1, 6):
        gates.decide(pid, number, True, "usr_qa", "ok")
    assert documents.save_version(other["id"], "y", "usr_qa")["reopened"] == [], "a document no gate rests on reopens nothing"
    assert documents.save_version(other["id"], "y", "usr_qa")["version"] == 2


def test_editing_a_document_whose_gate_is_not_approved_reopens_nothing(client, project):
    pid = project["id"]
    cases = documents.create(pid, "test_code", "Tests", "a", "usr_qa")
    gates.decide(pid, 0, True, "usr_qa", "ok")
    assert documents.save_version(cases["id"], "b", "usr_qa")["reopened"] == []
    assert gates.status(pid)[0]["status"] == "approved"


def test_nothing_approves_by_default(client, project):
    """A review that scores 100 on every item still leaves the gate pending until a named person decides."""
    run, _ = go_to_gate(client, project, 3, base_rules())
    assert pending(run)["payload"]["confidence"]["verdict"] == "APPROVED"
    assert next(g for g in client.get(f"/api/projects/{project['id']}/gates").json() if g["gate"] == 3)["status"] == "pending"
