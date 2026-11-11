"""Shared fixtures and helpers for the confidence tests."""

import pytest

from backend.maf import llm

from tests import reviewing
from tests.scripted_client import ScriptedClient
from tests.helpers_api import CASES, PLAN, REQUIREMENTS, TESTS, pending, upload_repo, wait_run


CALC = "def add(a, b):\n    return a + b\n"


def design_item(**change):
    item = {"tc_id": "C1", "component": {"file": "calc.py", "line": 2, "symbol": "add"}, "scores": dict(reviewing.PERFECT["design"]), "total": 100, "verdict": "APPROVED", "flaws": []}
    return {**item, **change}


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "calc.py").write_text(CALC, encoding="utf-8")
    return tmp_path


# integration: the QE workflow with a scripted reviewer


def base_rules(designer=CASES, grade=None, seen=None, extra=()):
    return [*extra, *reviewing.rules(grade, seen), ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", REQUIREMENTS),
            ("You are a principal test architect", PLAN), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
            ("You are a test design architect", designer), ("You are a test automation engineer", TESTS)]


def go_to_gate(client, project, number, rules, approve_reason=""):
    upload_repo(client, project, {"calc.py": CALC, "conftest.py": ""})
    scripted = ScriptedClient(rules)
    llm.set_client_override(scripted)
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(7):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        if pending(run)["gate"] == number:
            return run, scripted
        assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True, "feedback": approve_reason}).status_code == 200
    raise AssertionError("gate not reached")
