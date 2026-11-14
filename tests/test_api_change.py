"""Change workflow and the QE lifecycle through the real API."""

from backend.config import project_dir
from backend.maf import engine, llm
from tests.helpers_validity import make_run_env
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


def test_brownfield_qe_lifecycle_g0_to_g5_is_not_executed_and_the_tests_download(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    make_run_env(project_dir(project["id"]) / "worktrees" / "x")  # the .venv the run's worktree sits beside
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
            assert approval["payload"]["trace"]["stage"] == "requirements" and "Trace:" in approval["summary"]
        if approval["gate"] == 2:  # the scripted plan skips two levels with 5-character reasons: the plugin's check says so
            check = approval["payload"]["plugin_check"]
            assert check["ok"] is False and any("no Integration scenarios and no written reason" in g for g in check["gaps"]), check
            assert "agentic-qe Gate 2 check: FAIL" in approval["summary"]
            trace = approval["payload"]["trace"]
            assert (trace["stage"], trace["upstream"], trace["carried"], trace["changed"], trace["new"], trace["verdict"]) == ("plan", 1, 1, 0, 1, "PASS"), trace
        if approval["gate"] == 3:  # cases, the reviewer's records and the auditor's verdicts are in the plugin's files; only G2's short reasons remain
            check, audit = approval["payload"]["plugin_check"], approval["payload"]["design_audit"]
            assert check["error"] is None and audit["counts"]["COVERS"] == 4 and audit["unaudited"] == [], (check, audit)
            assert check["gaps"] and all("skippedLevels" in g for g in check["gaps"]), check["gaps"]
        if approval["gate"] == 0:
            assert "dependency installers" in approval["summary"] and "No test body is run" in approval["summary"]
        if approval["gate"] == 4:
            assert "run on this machine" not in approval["summary"], "brownfield tests are never run here"
        if approval["gate"] == 5:
            payload = approval["payload"]
            assert payload["summary"]["verdict"] == "NOT EXECUTED" and "Verdict NOT EXECUTED" in approval["summary"]
            assert (payload["summary"]["requirements"], payload["summary"]["cases"], payload["summary"]["tests"], payload["summary"]["valid"], payload["summary"]["needs_review"]) == (1, 4, 4, 4, 0), payload["summary"]
            assert payload["summary"]["by_check"] == {"V2b": 0, "V3": 0, "V4": 0, "V5": 0, "V6": 0}
            row = payload["matrix_rows"][0]
            assert row["covered"] and [c["test_file"] for c in row["cases"]][0].startswith("tests/agentic_qe/") and {c["result"] for c in row["cases"]} == {"valid"}
            assert payload["tests_zip"] == f"/api/runs/{run['id']}/tests.zip" and payload["run_command"] == "python -m pytest tests/agentic_qe"
            assert payload["plugin_check"]["ok"] is None and "tests are not executed here" in payload["plugin_check"]["note"], "execution gaps are not failures"
            assert payload["trace"]["stage"] == "sign" and payload["trace"]["verdict"] == "PASS" and "Trace:" in approval["summary"], "the carry-forward line holds with Prepare, Execute and Heal skipped"
            assert client.get(payload["tests_zip"]).status_code == 200, "the zip is downloadable at Gate 5"
        assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200
    run = wait_run(client, run["id"], ("completed", "failed"))
    assert run["status"] == "completed", run["error"]
    assert seen == [0, 1, 2, 3, 4, 5]
    started = [e["message"] for e in engine.events(run["id"]) if e["message"].startswith("Started ")]
    assert not {"Started Prepare environment", "Started Execute", "Started Heal test drift"} & set(started), started
    assert "Started Traceability" in started and "Started Release sign-off" in started
    assert [r["id"] for r in run["state"]["requirements"]] == ["REQ-001"], "the unverifiable requirement must be dropped"
    summary = run["state"]["summary"]
    assert summary["verdict"] == "NOT EXECUTED" and "executed" not in summary and "passed" not in summary
    assert all(g["status"] == "approved" for g in client.get(f"/api/projects/{project['id']}/gates").json())
    kinds = {d["kind"] for d in client.get(f"/api/projects/{project['id']}/documents").json()}
    assert {"discovery", "requirements", "test_plan", "test_cases", "test_code", "traceability", "release", "test_data"} <= kinds
    docs = client.get(f"/api/projects/{project['id']}/documents?kind=test_cases").json()
    table = client.get(f"/api/documents/{docs[0]['id']}/export/csv").text
    assert table.startswith("TC ID,User Story ID,Scenario,Type,Precondition,Test Data,Steps,Expected Result,Priority,Automation Candidate,Remarks") and "TC-APP-004" in table
    assert client.get(f"/api/documents/{docs[0]['id']}/export/jira").text.startswith("Summary,Issue Type,Description,Priority,Labels,Parent/Story ID")
    assert client.get(f"/api/runs/{run['id']}/changes.zip").status_code == 200


def test_qe_plan_naming_an_invented_requirement_fails_with_the_id(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    invented = PLAN.replace('"REQ-001"]', '"REQ-001", "REQ-099"]')
    assert invented != PLAN
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"),
        ("You are a requirements analyst", REQUIREMENTS),
        ("You are a principal test architect", invented),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(2):  # Gate 0 and Gate 1
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True}).status_code == 200
    run = wait_run(client, run["id"], ("failed", "waiting_approval"))
    assert run["status"] == "failed" and "REQ-099" in run["error"], run["error"]



def _to_gate3(client, project, verdict):
    from tests.reviewing import auditor
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"),
        ("You are a requirements analyst", REQUIREMENTS),
        ("You are a principal test architect", PLAN),
        ("Audit these designed cases.", auditor(verdict)),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
        ("You are a test design architect", CASES),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(4):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        if approval["gate"] == 3:
            return approval
        assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200
    raise AssertionError("no Gate 3")


def test_a_case_the_auditor_says_misses_is_redesigned_once(client, project):
    approval = _to_gate3(client, project, lambda i, n: "MISSES" if (i == "TC-APP-001" and n == 1) else "COVERS")
    audit = approval["payload"]["design_audit"]
    assert audit["first_audit"]["MISSES"] == 1 and audit["redesigned"] == 1 and audit["counts"]["MISSES"] == 0, audit


def test_a_case_that_still_misses_is_a_reject_a_person_must_answer(client, project):
    approval = _to_gate3(client, project, lambda i, n: "MISSES" if i == "TC-APP-001" else "COVERS")
    assert approval["payload"]["design_audit"]["counts"]["MISSES"] == 1
    refused = client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True})
    assert refused.status_code == 400 and "TC-APP-001" in refused.text, refused.text
