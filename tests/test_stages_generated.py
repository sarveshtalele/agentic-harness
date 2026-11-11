"""Generated test keywords, execution summaries and async mode."""

import json

import pytest

from backend.maf import llm
from backend.qe import execution
from tests.scripted_client import ScriptedClient
from tests.helpers_api import CASES, TESTS, pending, upload_repo, wait_run
from tests.helpers_confidence import CALC, base_rules
from tests.helpers_stages import junit_result


# static checks through the workflow


BAD = TESTS.replace("assert add(2, 3) == 5", "assert add(2, 3, c=4) == 5")


def run_to(client, project, number, rules):
    upload_repo(client, project, {"calc.py": CALC, "conftest.py": ""})
    scripted = ScriptedClient(rules)
    llm.set_client_override(scripted)
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(8):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        if pending(run)["gate"] == number:
            return run, scripted
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    raise AssertionError("gate not reached")


def fixed_file():
    first = json.loads(TESTS)["files"][0]
    return json.dumps({"framework": "pytest", "files": [first]})


def test_a_bad_keyword_goes_back_alone_with_the_real_signature(client, project):
    calls = []
    rules = base_rules(designer=CASES, extra=[("fix every problem the static checks found", lambda t: (calls.append(t), fixed_file())[1])])
    rules[-1] = ("You are a test automation engineer", BAD)
    run, _ = run_to(client, project, 4, rules)
    assert len(calls) == 1, "only the one bad test is sent back"
    sent = calls[0].rsplit("Rewrite only this generated test file", 1)[-1]
    assert "'c'" in sent and "Real signature: add(a, b)" in sent and "test_tc_app_001.py" in sent and "test_tc_app_002" not in sent
    payload = pending(run)["payload"]
    assert payload["emit_unresolved"] == [] and payload["estimate"]["used_so_far"] > 0
    doc = client.get(f"/api/documents/{payload['documents'][0]}").json()
    assert "c=4" not in doc["content"] and "assert add(2, 3) == 5" in doc["content"]


def test_a_test_that_is_still_wrong_after_one_round_stays_marked(client, project):
    calls = []
    rules = base_rules(extra=[("fix every problem the static checks found", lambda t: (calls.append(t), json.dumps({"framework": "pytest", "files": [json.loads(BAD)["files"][0]]}))[1])])
    rules[-1] = ("You are a test automation engineer", BAD)
    run, _ = run_to(client, project, 4, rules)
    assert len(calls) == 1
    marked = pending(run)["payload"]["emit_unresolved"]
    assert len(marked) == 1 and marked[0]["case_id"] == "TC-APP-001" and "Real signature: add(a, b)" in marked[0]["findings"][0]
    saved = client.get(f"/api/documents/{pending(run)['payload']['documents'][0]}").json()
    assert "STATIC CHECK FINDINGS" in saved["content"] and [t for t in saved["data"] if t.get("unresolved")] == [{"case_id": "TC-APP-001", "path": "tests/agentic_qe/test_tc_app_001.py", "unresolved": True}]


# the execution summary


def summary_rules(reply):
    return base_rules(extra=[("You are a QA execution engineer", reply)])


def at_gate5(client, project, reply):
    run, _ = run_to(client, project, 5, summary_rules(reply))
    return pending(run)["payload"]


def test_the_agents_execution_summary_is_used_when_it_matches_the_junit_counts(client, project):
    good = json.dumps({"summary": "4 passed, 0 failed, 0 skipped. All tests passed.", "passed": 4, "failed": 0, "skipped": 0, "verdict": "PASS"})
    payload = at_gate5(client, project, good)
    assert payload["execution_summary"]["source"] == "agent" and payload["execution_summary"]["text"].startswith("4 passed")
    assert payload["failure_classes"] == {"defect": 0, "test problem": 0, "environment": 0} and payload["defect_records"] == []


@pytest.mark.parametrize("reply", [
    {"summary": "All good.", "passed": 3, "failed": 1, "skipped": 0, "verdict": "PASS"},
    {"summary": "All 9 tests passed.", "passed": 4, "failed": 0, "skipped": 0, "verdict": "PASS"},
    {"summary": "4 passed, 2 failed.", "passed": 4, "failed": 0, "skipped": 0, "verdict": "PASS"},
    {"summary": "Everything fine.", "passed": 4, "failed": 0, "skipped": 0, "verdict": "FAIL"},
])
def test_a_summary_that_does_not_match_the_counts_is_refused(client, project, reply):
    payload = at_gate5(client, project, json.dumps(reply))
    assert payload["execution_summary"]["source"] == "code" and "refused" in payload["execution_summary"]["reason"]
    assert payload["execution_summary"]["text"].startswith("pytest: PASS. 4 passed, 0 failed, 0 skipped")


def test_summary_checks_in_isolation():
    result = {**junit_result("assert 1 == 2"), "passed": 2}
    ok = {"summary": "2 passed, 1 failed. FAIL.", "passed": 2, "failed": 1, "skipped": 0, "verdict": "FAIL"}
    assert execution.summary_problems(ok, result) == []
    assert execution.summary_problems({**ok, "summary": "3 tests ran, 5 failed"}, result)
    assert "defect" in execution.code_summary(result)


def test_prepare_sets_async_mode_for_the_generated_tests_only_and_the_async_test_really_passes(client, project, tmp_path):
    from backend.maf.engine import RunContext
    from backend.maf.workflows import qe

    from backend.db import db, now

    pytest.importorskip("pytest_asyncio")
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, state, started_at) VALUES ('run_prep', ?, 'qe', 'running', '{}', '{}', ?)", (project["id"], now()))
    (tmp_path / "tests/agentic_qe").mkdir(parents=True)
    (tmp_path / "tests/agentic_qe/test_a.py").write_text("import asyncio\n\n\nasync def test_a():\n    await asyncio.sleep(0)\n    assert 1 + 1 == 2\n")
    update = client.portal.call(qe.qe_prepare, RunContext("run_prep", project["id"], "prepare"), {"worktree": str(tmp_path), "mode": "brownfield"})
    assert update["pytest_args"] == ["-o", "asyncio_mode=auto"] and update["async_tests"] == ["tests/agentic_qe/test_a.py"] and update["env_facts"]["pytest_asyncio"]
    result = execution.run_suite("pytest", tmp_path, "tests/agentic_qe", tmp_path / "out", 120, tuple(update["pytest_args"]))
    assert (result["passed"], result["failed"], result["verdict"]) == (1, 0, "PASS")
    assert not list(tmp_path.glob("*.ini")) and not (tmp_path / "pyproject.toml").exists(), "the repository's own config is not edited"
