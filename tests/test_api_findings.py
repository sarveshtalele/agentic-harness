"""Fix-all on findings and the editable case table."""

import json

import pytest
from tests.helpers_api import client, make_user, project, sign_in, unique  # noqa: F401 - fixtures


def test_signer_is_the_signed_in_account_never_a_typed_name(client):
    name = unique()
    user = make_user(client, name)
    other, _ = sign_in(name)
    mine = other.post("/api/projects", json={"name": "Mine", "description": ""}).json()
    doc = other.post(f"/api/projects/{mine['id']}/documents", json={"kind": "brd", "title": "D", "content": "# T\n", "author": "someone else"}).json()
    assert doc["author"] == user["id"]
    gates_after = other.post(f"/api/projects/{mine['id']}/gates/0/decision", json={"approved": True, "by": "someone else", "reason": "ok"}).json()
    assert gates_after[0]["decided_by"] == user["id"] and gates_after[0]["decided_by_name"] == name and gates_after[0]["signature_valid"]
    approved = other.post(f"/api/documents/{doc['id']}/approve", json={"by": "someone else"}).json()
    assert approved["status"] == "approved"
    assert other.put(f"/api/documents/{doc['id']}", json={"content": "# T2\n", "author": "someone else"}).json()["author"] == user["id"]
    assert other.post(f"/api/documents/{doc['id']}/restore/1", json={"by": "someone else"}).json()["author"] == user["id"]
    shown = other.get(f"/api/documents/{doc['id']}").json()
    assert shown["author_name"] == name
    ledger_entries = other.get(f"/api/projects/{mine['id']}/ledger").json()["entries"]
    assert {e["actor"] for e in ledger_entries} == {user["id"]}, "every entry names the account"
    assert name in {e["actor_name"] for e in ledger_entries} and "someone else" not in json.dumps(ledger_entries)
    changed = client.put("/api/agents/confidence-reviewer/settings", json={"enabled": True, "by": "someone else", "reason": "check"}).json()
    assert changed["settings_by"] == "admin" and changed["settings_by_name"] == "Administrator", "the admin's login name is never displayed"
    prompt = client.post("/api/prompts/confidence-reviewer", json={"body": "You are an independent reviewer. Same text.", "note": "n", "author": "someone else"}).json()
    assert prompt["author"] == "admin"


def seed_findings(project_id: str, files: list[str]) -> list[str]:
    from backend.db import db, new_id, now

    ids = []
    with db() as con:
        for name in files:
            ids.append(new_id("fnd"))
            con.execute("INSERT INTO findings (id, project_id, source, rule, severity, title, file, line, evidence, status, fingerprint, created_at) VALUES (?,?,?,?,?,?,?,?,?,'open',?,?)",
                        (ids[-1], project_id, "t", "r", "high", f"Bug in {name}", name, 1, "x", ids[-1], now()))
    return ids


@pytest.mark.parametrize("verdict,expected", [("PASS", "fixed"), ("NO NEW FAILURES", "fixed"), ("FAIL", "fix_attempted"), ("INCOMPLETE", "fix_attempted")])
def test_fix_all_marks_findings_fixed_only_when_tests_pass(client, project, tmp_path, verdict, expected):
    import asyncio

    from backend.maf.engine import RunContext
    from backend.maf.workflows import change
    from backend.repos import git

    (tmp_path / "one.py").write_text("x = 1\n")
    git.init_snapshot(tmp_path, "base")
    (tmp_path / "one.py").write_text("x = 2\n")
    one, two = seed_findings(project["id"], ["one.py", "two.py"])
    from backend.db import db, new_id, now

    run_id = new_id("run")
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, started_at) VALUES (?,?,?,?,?,?)", (run_id, project["id"], "change", "running", "{}", now()))
    state = {"worktree": str(tmp_path), "title": "Fix", "branch": "b", "finding_ids": [one, two], "verification": {"verdict": verdict}}
    asyncio.run(change.change_deliver(RunContext(run_id, project["id"]), state, {"by": "admin"}))
    status = {f["id"]: f["status"] for q in ("open", "fixed") for f in client.get(f"/api/projects/{project['id']}/findings?status={q}").json()}
    assert status[one] == expected and status[two] == "open", "a finding in an untouched file stays open"
    still_open = {f["id"] for f in client.get(f"/api/projects/{project['id']}/findings").json()}
    assert (one in still_open) == (expected == "fix_attempted") and two in still_open, "fix attempted still counts as open"
    assert one in {f["id"] for f in client.get("/api/findings").json()} or expected == "fixed"
    with db() as con:
        con.execute("UPDATE findings SET status='dismissed' WHERE id=?", (two,))
    assert [f["id"] for f in change._chosen_findings(project["id"], {"fix_all": True})] == ([one] if expected == "fix_attempted" else []), "Fix all picks up a failed attempt again"


CASE_TABLE = ("| TC ID | Requirement | Scenario | Type | Level | Precondition | Test Data | Steps | Expected Result | Oracle | Priority |\n|---|---|---|---|---|---|---|---|---|---|---|\n"
              "| TC-APP-001 | R1 | Reset a password | Positive | E2E | A member exists | {} | 1. Open the link 2. Set a password | The password changes | specified | P1 |")


CASE = {"id": "TC-APP-001", "requirement_id": "R1", "area_id": "A1", "scenario": "Reset a password", "type": "Positive", "level": "E2E", "precondition": "A member exists", "test_data": "{}",
        "steps": ["Open the link", "Set a password"], "expected_result": "The password changes", "oracle": "specified", "priority": "P1"}


def test_editing_the_case_table_updates_the_csv_export(client, project):
    from backend.core import documents

    made = documents.create(project["id"], "test_cases", "Cases", CASE_TABLE, "agent:test-design-architect", data=[CASE])
    same = client.put(f"/api/documents/{made['id']}", json={"content": CASE_TABLE + "\n", "note": "no change"}).json()
    assert same["data"] == [CASE], "an unchanged table keeps the stored case, including columns the table does not show"
    edited = CASE_TABLE.replace("The password changes", "The member can sign in with the new password").replace("2. Set a password", "2. Set a password 3. Sign in")
    saved = client.put(f"/api/documents/{made['id']}", json={"content": edited, "note": "edit"}).json()
    assert saved["data"][0]["expected_result"] == "The member can sign in with the new password" and saved["data"][0]["steps"][-1] == "Sign in" and saved["data"][0]["area_id"] == "A1"
    csv_text = client.get(f"/api/documents/{made['id']}/export/csv").text
    assert "The member can sign in with the new password" in csv_text and "3. Sign in" in csv_text
    assert "The member can sign in" in client.get(f"/api/documents/{made['id']}/export/jira").text
    assert "The member can sign in" not in client.get(f"/api/documents/{made['id']}/export/csv?version=1").text, "an older version still exports its own data"


def test_a_case_table_that_does_not_validate_is_refused(client, project):
    from backend.core import documents

    made = documents.create(project["id"], "test_cases", "Cases", CASE_TABLE, "agent:test-design-architect", data=[CASE])
    for bad, problem in ((CASE_TABLE.replace("| E2E |", "| Everywhere |"), "level"), (CASE_TABLE.replace("The password changes", "works"), "concrete"),
                         (CASE_TABLE + "\n| TC-APP-002 | R1 |", "cells"), ("Just prose now.", "table"), (CASE_TABLE.replace("| P1 |", "| P9 |"), "priority")):
        response = client.put(f"/api/documents/{made['id']}", json={"content": bad})
        assert response.status_code == 400 and problem in response.json()["detail"], (problem, response.text)
    current = client.get(f"/api/documents/{made['id']}").json()
    assert current["version"] == 1 and current["data"] == [CASE], "nothing was stored"
