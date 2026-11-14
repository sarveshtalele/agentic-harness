"""Change workflow and the QE lifecycle through the real API."""

from backend.maf import llm
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import CALC, CASES, client, edit_script, FIX_ADD, pending, PLAN, project, REQUIREMENTS, TESTS, upload_repo, wait_run  # noqa: F401 - fixtures


def test_change_workflow_really_runs_tests_then_commits_on_branch(client, project):
    from backend.config import repo_dir
    from backend.repos import git

    upload_repo(client, project, CALC)
    base = git.head(repo_dir(project["id"]))
    llm.set_client_override(ScriptedClient([("You diagnose failures", edit_script(FIX_ADD))]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix add", "spec": "add subtracts"}}).json()
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval", run["error"]
    approval = pending(run)
    assert approval["payload"]["verification"]["verdict"] == "PASS"
    assert "+    return a + b" in approval["payload"]["diff"]
    assert (repo_dir(project["id"]) / "calc.py").read_text().count("a - b") == 1, "the main checkout stays untouched"

    client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"], ("completed", "failed"))
    assert run["status"] == "completed", run["error"]
    assert run["state"]["commit"] != base and git.head(repo_dir(project["id"])) == base


def test_change_retries_only_for_what_it_broke(client, project):
    upload_repo(client, project, {**CALC, "calc.py": "def add(a, b):\n    return a + b\n"})
    wrong = ("replace_text", {"path": "calc.py", "search": "return a + b", "replace": "return a * b"})
    right = ("replace_text", {"path": "calc.py", "search": "return a * b", "replace": "return b + a"})
    llm.set_client_override(ScriptedClient([("You diagnose failures", edit_script(wrong, "Done.", right))]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix", "spec": "fix"}}).json()["id"])
    assert run["status"] == "waiting_approval", run["error"]
    assert pending(run)["payload"]["verification"]["verdict"] == "PASS" and run["state"]["attempt"] == 2


def test_change_refuses_escape_and_secret_edits(client, project):
    upload_repo(client, project, CALC)
    secret = "sk-" + "z" * 40
    bad = [("write_file", {"path": "../../evil.py", "content": "x"}), ("write_file", {"path": "k.py", "content": f"K='{secret}'"}), ("write_file", {"path": ".git/config", "content": "x"})]
    llm.set_client_override(ScriptedClient([("You diagnose failures", edit_script(*bad))]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix", "spec": "fix"}}).json()["id"], ("failed", "waiting_approval"))
    assert run["status"] == "failed" and "without changing any file" in run["error"] and secret not in run["error"]


def test_qe_lifecycle_all_six_gates_with_real_execution(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"),
        ("You are a requirements analyst", REQUIREMENTS),
        ("You are a principal test architect", PLAN),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
        ("You are a test design architect", CASES),
        ("You are a test automation engineer", TESTS),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    seen = []
    for _ in range(6):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        seen.append(approval["gate"])
        if approval["gate"] == 1:  # the agentic-qe plugin's own check-gate.ts verified the requirements on disk
            check = approval["payload"]["plugin_check"]
            assert check["error"] is None and check["ok"] is True and check["dropped"] == [], check
            assert "agentic-qe Gate 1 check: PASS." in approval["summary"]
        if approval["gate"] == 2:  # the scripted plan skips two levels with 5-character reasons: the plugin's check says so
            check = approval["payload"]["plugin_check"]
            assert check["ok"] is False and any("no Integration scenarios and no written reason" in g for g in check["gaps"]), check
            assert "agentic-qe Gate 2 check: FAIL" in approval["summary"]
        assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200
    run = wait_run(client, run["id"], ("completed", "failed"))
    assert run["status"] == "completed", run["error"]
    assert seen == [0, 1, 2, 3, 4, 5]
    assert [r["id"] for r in run["state"]["requirements"]] == ["REQ-001"], "the unverifiable requirement must be dropped"
    summary = run["state"]["summary"]
    assert summary["verdict"] == "PASS" and summary["executed"] == 4 and summary["coverage"] == 100.0
    assert all(g["status"] == "approved" for g in client.get(f"/api/projects/{project['id']}/gates").json())
    kinds = {d["kind"] for d in client.get(f"/api/projects/{project['id']}/documents").json()}
    assert {"discovery", "requirements", "test_plan", "test_cases", "test_code", "traceability", "release", "test_data"} <= kinds
    docs = client.get(f"/api/projects/{project['id']}/documents?kind=test_cases").json()
    table = client.get(f"/api/documents/{docs[0]['id']}/export/csv").text
    assert table.startswith("TC ID,User Story ID,Scenario,Type,Precondition,Test Data,Steps,Expected Result,Priority,Automation Candidate,Remarks") and "TC-APP-004" in table
    assert client.get(f"/api/documents/{docs[0]['id']}/export/jira").text.startswith("Summary,Issue Type,Description,Priority,Labels,Parent/Story ID")
    assert client.get(f"/api/runs/{run['id']}/changes.zip").status_code == 200
