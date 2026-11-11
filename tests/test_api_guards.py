"""Guarded edits, token budget, fixes and approvals."""

from backend.maf import llm
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import BUGGY, CALC, CASES, client, edit_script, FIX_ADD, pending, PLAN, project, REQUIREMENTS, rules, TESTS, upload_repo, wait_run  # noqa: F401 - fixtures


def test_guarded_apply_refuses_unsafe_edits(tmp_path):
    from backend.maf.workflows import Edit, guarded_apply

    create = lambda path, content: Edit(path=path, action="create", content=content)
    assert guarded_apply(tmp_path, [create("../evil.py", "x")])[1]
    assert guarded_apply(tmp_path, [create(".git/config", "x")])[1]
    assert guarded_apply(tmp_path, [create("k.py", "K='sk-" + "z" * 40 + "'")])[1]
    assert guarded_apply(tmp_path, [create("ok.py", "x = 1\n")]) == (["ok.py"], [])
    assert "exists" in guarded_apply(tmp_path, [create("ok.py", "y = 2\n")])[1][0] and (tmp_path / "ok.py").read_text() == "x = 1\n"
    assert "not found" in guarded_apply(tmp_path, [Edit(path="ok.py", action="replace", search="absent", replace="y")])[1][0]
    assert "not allowed" in guarded_apply(tmp_path, [Edit(path="ok.py", action="delete")])[1][0] and (tmp_path / "ok.py").exists()
    assert not (tmp_path.parent / "evil.py").exists()


def test_healing_guard_refuses_weakened_assertion(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    drifted = TESTS.replace("assert add(2, 3) == 5", "{}['seed']\\n    assert add(2, 3) == 5")
    weaken = ("replace_text", {"path": "tests/agentic_qe/test_tc_app_001.py", "search": "assert add(2, 3) == 5", "replace": "assert True"})
    app_edit = ("replace_text", {"path": "calc.py", "search": "a + b", "replace": "a - b"})
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", REQUIREMENTS), ("You are a principal test architect", PLAN),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'), ("You are a test design architect", CASES), ("You are a test automation engineer", drifted),
        ("You diagnose failures", edit_script(weaken, app_edit)),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(5):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval", run["error"]
    assert pending(run)["gate"] == 5 and run["state"]["summary"]["verdict"] == "FAIL"
    assert len(run["state"]["healer_log"][0]["refused"]) == 2 and run["state"]["healer_log"][0]["applied"] == []


def test_agent_text_uses_last_message_without_tool_narration(client, project):
    from backend.maf.runtime import AgentCall

    steps = iter([{"call": "list_files", "args": {}}, "Final answer."])
    llm.set_client_override(ScriptedClient([("You are a requirements analyst", lambda _: next(steps))]))
    upload_repo(client, project, CALC)
    assert client.portal.call(AgentCall(None, project["id"], "requirements-analyst", chat=True).text, "go") == "Final answer."


def test_run_stops_at_token_budget(client, project, monkeypatch):
    from backend.maf import runtime as agents

    monkeypatch.setattr(agents, "RUN_TOKEN_LIMIT", 1)
    upload_repo(client, project, BUGGY)
    scripted = ScriptedClient([("You review code for real defects", '{"findings": []}')])
    llm.set_client_override(scripted)
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan", "input": {"review_files": 4}}).json()
    run = wait_run(client, run["id"], ("completed", "failed"))
    assert len(scripted.calls) <= 4


def test_bug_review_gets_code_and_no_tools(client, project):
    upload_repo(client, project, BUGGY)
    scripted = ScriptedClient([("You review code for real defects", '{"findings": []}')])
    llm.set_client_override(scripted)
    wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"}).json()["id"], ("completed", "failed"))
    assert any("9: " in call and "return a / b" in call for call in scripted.calls)


def test_fix_must_touch_the_finding_file(client, project):
    upload_repo(client, project, {**CALC, "admin.py": "import subprocess\n\n\ndef b(p):\n    return subprocess.call('x ' + p, shell=True)\n"})
    llm.set_client_override(ScriptedClient([("You review code for real defects", '{"findings": []}'), ("You diagnose failures", edit_script(FIX_ADD))]))
    wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"}).json()["id"], ("completed", "failed"))
    finding = next(f for f in client.get(f"/api/projects/{project['id']}/findings").json() if f["file"] == "admin.py")
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "finding_id": finding["id"], "title": "Fix"}}).json()
    run = wait_run(client, run["id"], ("failed", "waiting_approval"))
    assert run["status"] == "failed" and "without changing any file" in run["error"]
    calc = client.get(f"/api/projects/{project['id']}/repo/file", params={"path": "calc.py"}).text
    assert "a - b" in calc


def test_global_approvals_and_cancel(client, project):
    llm.set_client_override(ScriptedClient(rules()))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "ba", "input": {"brief": "x"}}).json()["id"])
    items = [a for a in client.get("/api/approvals").json() if a["run_id"] == run["id"]]
    assert items[0]["project_name"] == "Shop" and items[0]["gate"] == 0
    assert client.post(f"/api/runs/{run['id']}/cancel").json()["status"] == "cancelled"
    assert not [a for a in client.get("/api/approvals").json() if a["run_id"] == run["id"]]
    assert client.post(f"/api/approvals/{items[0]['id']}/decide", json={"approved": True}).status_code == 400


def test_edit_agents_have_no_read_tools_and_get_the_finding_file(client, project):
    upload_repo(client, project, {**CALC, "admin.py": "import subprocess\n\n\ndef b(p):\n    return subprocess.call('x ' + p, shell=True)\n"})
    scripted = ScriptedClient([("You review code for real defects", '{"findings": []}'), ("You diagnose failures", edit_script(("replace_text", {"path": "admin.py", "search": "return subprocess.call('x ' + p, shell=True)", "replace": "return subprocess.call(['x', p])"})))])
    llm.set_client_override(scripted)
    wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"}).json()["id"], ("completed", "failed"))
    finding = next(f for f in client.get(f"/api/projects/{project['id']}/findings").json() if f["file"] == "admin.py")
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "finding_id": finding["id"], "title": "Fix"}}).json()["id"], ("failed", "waiting_approval"))
    assert run["status"] == "waiting_approval", run["error"]
    approval = pending(run)
    assert "diff --git a/admin.py" in approval["payload"]["diff"]
    check = approval["payload"]["verification"]
    assert check["verdict"] == "NO NEW FAILURES" and check["existing_failures"] == 1 and run["state"]["attempt"] == 1, "an already failing test is not blamed on this change"
    assert any("--- FILE admin.py ---" in call for call in scripted.calls)
    import backend.maf.governance as governance

    assert not governance.POLICIES["feature-engineer"].workflow_tools & governance.READ
