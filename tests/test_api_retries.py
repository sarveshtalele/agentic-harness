"""Retries, environment failures, model limits and observability records."""

import json

from backend.maf import llm

from tests.scripted_client import ScriptedClient
from tests.helpers_api import CALC, client, edit_script, FIX_ADD, GOOD_REVIEW, pending, project, upload_repo, wait_run  # noqa: F401 - fixtures


def worker_call(scripted) -> str:
    """The last call to the working agent. Confidence reviews run beside it."""
    return next(call for call in reversed(scripted.calls) if not call.startswith("You are an independent reviewer"))


def test_feature_selects_files_on_large_repo(client, project):
    files = {f"mod_{i}.py": f"x = {i}\n" for i in range(20)}
    upload_repo(client, project, {**files, **CALC})
    scripted = ScriptedClient([("You are a repository intelligence analyst", '{"files": ["calc.py", "missing.py"]}'), ("You implement features in existing codebases", edit_script(FIX_ADD, ("write_file", {"path": "tests/test_more.py", "content": "def test_more():\n    assert 1 + 1 == 2\n"})))])
    llm.set_client_override(scripted)
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "feature", "title": "Fix", "spec": "fix add"}}).json()["id"])
    assert run["status"] == "waiting_approval", run["error"]
    assert run["state"]["paths"] == ["calc.py"]


def test_environment_failures_are_inconclusive_and_not_retried(client, project):
    upload_repo(client, project, {"app.py": "import not_installed_anywhere\n\nVALUE = 1\n", "tests/test_app.py": "import app\n\n\ndef test_value():\n    assert app.VALUE == 1\n", "conftest.py": ""})
    scripted = ScriptedClient([("You implement features", edit_script(("write_file", {"path": "tests/test_new.py", "content": "import app\n\n\ndef test_new():\n    assert app.VALUE == 1\n"})))])
    llm.set_client_override(scripted)
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "feature", "title": "T", "spec": "add a test"}}).json()["id"])
    assert run["status"] == "waiting_approval", run["error"]
    check = pending(run)["payload"]["verification"]
    assert check["verdict"] == "INCONCLUSIVE" and "environment" in check["reason"] and run["state"]["attempt"] == 1


def test_incomplete_feature_is_not_called_pass(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n", "conftest.py": ""})
    edit = ("replace_text", {"path": "calc.py", "search": "return a + b", "replace": "return b + a"})
    llm.set_client_override(ScriptedClient([("You implement features", edit_script(edit, ("write_file", {"path": "notes.txt", "content": "scratch"})))]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "feature", "title": "T", "spec": "Add multiply_numbers(a, b) with tests"}}).json()["id"])
    assert run["status"] == "waiting_approval", run["error"]
    check = pending(run)["payload"]["verification"]
    assert check["verdict"] == "INCOMPLETE" and "multiply_numbers" in check["reason"] and "no test file" in check["reason"]
    assert "notes.txt" not in pending(run)["payload"]["diff"]


def test_changed_assertions_are_shown_to_the_reviewer(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n", "conftest.py": ""})
    weaken = ("replace_text", {"path": "tests/test_calc.py", "search": "assert add(2, 3) == 5", "replace": "assert add(2, 3) > 0"})
    llm.set_client_override(ScriptedClient([("You implement features", edit_script(weaken))]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "feature", "title": "T", "spec": "x"}}).json()["id"])
    assert pending(run)["payload"]["verification"]["changed_assertions"] == ["assert add(2, 3) == 5"]


def test_edit_refused_by_a_guard_is_retried_with_current_files(client, project):
    upload_repo(client, project, CALC)
    stale = ("replace_text", {"path": "calc.py", "search": "1: return a - b", "replace": "return a + b"})
    scripted = ScriptedClient([("You diagnose failures", edit_script(stale, "Done.", FIX_ADD))])
    llm.set_client_override(scripted)
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix", "spec": "fix"}}).json()["id"])
    assert pending(run)["payload"]["verification"]["verdict"] == "PASS" and run["state"]["attempt"] == 1
    last = worker_call(scripted)
    assert "CURRENT FILES" in last and "not found" in last


def test_retry_sees_the_failing_test_file_first(client, project):
    big = {f"big_{i}.py": "x = 1\n" * 3000 for i in range(4)}
    guard = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    upload_repo(client, project, {**big, "calc.py": "def add(a, b):\n    return a + b\n", "tests/test_guard.py": guard, "conftest.py": ""})
    picks = '{"files": ["calc.py", "big_0.py", "big_1.py", "big_2.py", "big_3.py"]}'
    breaks = ("replace_text", {"path": "calc.py", "search": "return a + b", "replace": "return a * b"})
    repair = ("replace_text", {"path": "calc.py", "search": "return a * b", "replace": "return b + a"})
    scripted = ScriptedClient([("You are a repository intelligence analyst", picks), ("You diagnose failures", edit_script(breaks, "Done.", repair))])
    llm.set_client_override(scripted)
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix", "spec": "fix"}}).json()["id"])
    assert run["status"] == "waiting_approval", run["error"]
    assert run["state"]["paths"][0] == "tests/test_guard.py" and "--- FILE tests/test_guard.py ---" in worker_call(scripted)


def test_cut_off_reply_is_never_parsed_as_complete(client, project):
    from backend.maf.runtime import AgentCall
    from backend.maf.workflows import Review

    replies = iter([{"cut_off": GOOD_REVIEW}, GOOD_REVIEW])
    scripted = ScriptedClient([("Review this", lambda _: next(replies))])
    llm.set_client_override(scripted)
    result = client.portal.call(AgentCall(None, project["id"], "confidence-reviewer").typed, "Review this", Review)
    assert result.score == 90 and "cut off at the token limit" in scripted.calls[-1]


def test_model_calls_respect_the_process_limit(client, project, monkeypatch):
    import asyncio

    from backend.maf import runtime

    monkeypatch.setattr("backend.maf.runtime.gate.MODEL_CONCURRENCY", 2)
    runtime._gates.clear()
    active, peak = [0], [0]

    async def scenario():
        async def slow(*_, **__):
            active[0] += 1
            peak[0] = max(peak, active)[0]
            await asyncio.sleep(0.02)
            active[0] -= 1
            return await real("x", session=None)

        calls = [runtime.AgentCall(None, project["id"], "confidence-reviewer") for _ in range(5)]
        real = calls[0].agent.run
        for call in calls:
            call.agent.run = slow
        await asyncio.gather(*(call.text("x") for call in calls))

    llm.set_client_override(ScriptedClient([("x", "ok")]))
    client.portal.call(scenario)
    assert peak[0] == 2


def test_observability_records_every_kind_and_filters(client, project):
    from backend.maf.observability import record_tool

    upload_repo(client, project, CALC)
    llm.set_client_override(ScriptedClient([("You diagnose failures", edit_script(FIX_ADD))]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix", "spec": "fix"}}).json()["id"])
    secret = "sk-" + "z" * 40
    record_tool("project-copilot", project["id"], run["id"], "chat", "read_file", {"path": "calc.py", "key": secret}, 12)
    record_tool("project-copilot", project["id"], run["id"], "chat", "grep", {}, 3, "Bad pattern")

    log = client.get(f"/api/observability?project_id={project['id']}").json()
    assert log["counts"]["agent"] >= 1 and log["counts"]["tool"] == 2 and log["counts"]["workflow"] >= 1 and log["counts"]["approval"] >= 1 and log["counts"]["audit"] >= 1
    assert log["counts"]["mcp"] == 0 and log["errors"] >= 1 and log["tokens"] > 0
    assert log["integrity"][0]["valid"] is True and log["items"][0]["project"] == project["name"]
    assert secret not in json.dumps(log), "arguments are stored redacted"

    tools = client.get(f"/api/observability?run_id={run['id']}&kind=tool").json()["items"]
    assert {t["name"] for t in tools} == {"read_file", "grep"} and next(t for t in tools if t["name"] == "grep")["level"] == "error"
    assert client.get(f"/api/observability?q=Bad%20pattern&project_id={project['id']}").json()["total"] == 1
    assert client.get("/api/observability?project_id=prj_missing").json()["items"] == []
    export = client.get(f"/api/observability/export?run_id={run['id']}")
    assert "attachment" in export.headers["content-disposition"] and export.json()["filters"]["run_id"] == run["id"]


def test_skills_appear_for_qe_stages(client, project):
    from backend.db import db, now
    from backend.maf.observability import query

    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, state, started_at) VALUES ('run_obs', ?, 'qe', 'completed', '{}', '{}', ?)", (project["id"], now()))
        con.execute("INSERT INTO run_events (run_id, seq, type, stage, message, ts) VALUES ('run_obs', 1, 'stage_start', 'plan', 'Started Test plan', ?)", (now(),))
    assert [i["name"] for i in query(run_id="run_obs", kind="skill")["items"]] == ["planning-tests"]
