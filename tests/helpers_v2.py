"""Helpers for the QE v2 step 3 tests: drive a scripted brownfield run to a gate."""
import json

from backend.config import project_dir
from backend.maf import llm
from tests.helpers_api import CASES, PLAN, REQUIREMENTS, TESTS, pending, upload_repo, wait_run
from tests.helpers_validity import make_run_env
from tests.reviewing import auditor, code_auditor, rules as case_rules
from tests.scripted_client import ScriptedClient

CALC = {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""}
TWO = {"calc.py": "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n", "conftest.py": ""}


def case(**kw):
    return {"id": "TC-APP-001", "requirement_id": "REQ-001", "scenario": "s", "type": "Positive", "level": "Unit", "steps": ["call add(2,3)"], "expected_result": "returns 5", "oracle": "specified", "test_data": "2, 3", **kw}


def start(client, project, extra, *, repo=CALC, plan=PLAN, requirements=REQUIREMENTS, cases=CASES, tests=TESTS, design_auditor=None, code_audit=None, reviews=()):
    upload_repo(client, project, repo)
    make_run_env(project_dir(project["id"]) / "worktrees" / "x")
    sc = ScriptedClient([
        *extra,
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"),
        ("You are a requirements analyst", requirements),
        ("You are a principal test architect", plan),
        ("Audit these designed cases.", design_auditor or auditor()),
        ("Audit these generated tests.", code_audit or code_auditor()),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
        ("You are a test design architect", cases),
        ("You are a test automation engineer", tests),
    ])
    llm.set_client_override(sc)
    return sc, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()


def to_gate(client, run, gate):
    while True:
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        if approval["gate"] == gate:
            return run, approval
        assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200


def cases_json(*cases):
    return json.dumps({"cases": list(cases)})
