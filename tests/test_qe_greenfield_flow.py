"""A greenfield (spec-first) QE run keeps Prepare, Execute and Heal after Gate 4; brownfield skips them (tests/test_api_change.py)."""
import json

from backend.core import documents
from backend.maf import engine, llm
from tests.helpers_api import BRD, CASES, PLAN, REQUIREMENTS, TESTS, client, pending, project, wait_run  # noqa: F401 - fixtures
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient


ONE = json.dumps({"requirements": [json.loads(REQUIREMENTS)["requirements"][0] | {"tier": "specified"}]})  # greenfield keeps what the documents say; nothing is verified against code


def test_greenfield_run_still_goes_through_prepare_and_execute_and_ends_inconclusive(client, project):
    doc = documents.create(project["id"], "brd", "Calculator BRD", BRD, "tester")
    documents.set_status(doc["id"], "approved", "tester")
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", ONE), ("You are a principal test architect", PLAN),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
        ("You are a test design architect", CASES), ("You are a test automation engineer", TESTS)]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe", "input": {"spec_first": True}}).json()
    gates = []
    for _ in range(6):
        run = wait_run(client, run["id"], ("waiting_approval", "completed", "failed"), timeout=120)
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        gates.append(approval["gate"])
        decided = client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True, "feedback": "Spec-first baseline: the code does not exist yet, so the tests fail"})
        assert decided.status_code == 200, (approval["gate"], decided.text)
        if approval["gate"] == 5:
            break
    run = wait_run(client, run["id"], ("completed", "failed"), timeout=120)
    assert run["status"] == "completed", run["error"]
    assert gates == [0, 1, 2, 3, 4, 5]
    started = [e["message"] for e in engine.events(run["id"]) if e["message"].startswith("Started ")]
    assert "Started Prepare environment" in started and "Started Execute" in started, started
    assert run["state"]["summary"]["verdict"] == "INCONCLUSIVE" and "No code under test" in run["state"]["summary"]["reason"]
    after = run["state"]["tests_review_after"]
    assert after["capped"] >= 1 and after["failed"] >= 1, "greenfield tests that fail when run are capped, as before"
