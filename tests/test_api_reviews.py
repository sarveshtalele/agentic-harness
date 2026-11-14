"""Confidence reviews and QE design and test batches."""

import json

import re

from backend.maf import llm
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import CALC, CASES, client, edit_script, FIX_ADD, pending, PLAN, project, REQUIREMENTS, TESTS, upload_repo, wait_run  # noqa: F401 - fixtures


def test_every_qe_gate_shows_a_confidence_review(client, project):
    from backend.core.doc_checks import DISCOVERY_HEADINGS

    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    scores = iter([40] + [92] * 30)
    review = lambda _: json.dumps({"score": next(scores), "verdict": "APPROVED", "issues": ["checked"]})
    ninety_two = {"design": {"fixture_validity": 12}, "code": {"import_safety": 12}, "plan": {"level_fit": 22}}  # each per-case record totals 92
    good = "\n".join(f"## {h}\ntext `calc.py`" for h in DISCOVERY_HEADINGS)
    scripted = ScriptedClient([("You are a repository intelligence analyst", good), ("You are a requirements analyst", REQUIREMENTS), ("You are a principal test architect", PLAN),
                               *case_rules(lambda kind, key: {"scores": ninety_two[kind]}), ("You are an independent reviewer", review), ("You are a test design architect", CASES), ("You are a test automation engineer", TESTS)])
    llm.set_client_override(scripted)
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    seen = {}
    for _ in range(6):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        seen[approval["gate"]] = approval["payload"].get("confidence")
        if approval["gate"] == 4:
            break
        client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True})
    assert all(seen[g]["score"] == 92 for g in (1, 2, 3, 4)), seen
    assert sum("Rewrite the complete discovery summary" in c for c in scripted.calls) >= 1, "a low score sends the work back"
    gate_one = next(a for a in run["approvals"] if a["gate"] == 1)
    assert "Discovery summary" in gate_one["payload"]["titles"]


def test_failed_review_is_shown_as_not_run_never_as_a_score(client, project):
    upload_repo(client, project, CALC)
    llm.set_client_override(ScriptedClient([("You diagnose failures", edit_script(FIX_ADD))]))
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "change", "input": {"kind": "bugfix", "title": "Fix", "spec": "fix"}}).json()["id"])
    confidence = pending(run)["payload"]["verification"]["confidence"]
    assert confidence["verdict"] == "NOT RUN" and confidence["score"] is None


def test_design_splits_a_batch_that_keeps_breaking(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    ids = ["REQ-001", "REQ-002"]
    requirements = json.dumps({"requirements": [{"id": i, "title": i, "statement": f"add for {i}", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"} for i in ids]})
    plan = json.dumps({"strategy": "Unit first", "areas": [{"id": "A1", "name": "Add", "requirement_ids": ids, "risk": "P0", "level": "Unit", "framework": "pytest", "rationale": "Pure logic"}], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}})

    def designer(text: str) -> str:
        section = text.rsplit("Design test cases for only these requirements", 1)[-1].split("PLAN:")[0]
        wanted = [i for i in ids if i in section]
        if len(wanted) > 1:
            return '{"cases": [{"id": "A", "requirement_id": "REQ-001", broken'
        return json.dumps({"cases": [{"id": "x", "requirement_id": wanted[0], "scenario": f"{wanted[0]} {k}", "type": k, "level": "Unit", "steps": ["call add"], "expected_result": "correct", "oracle": "specified"} for k in ("Positive", "Negative", "Negative (Boundary)", "Exception")]})

    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", requirements), ("You are a principal test architect", plan),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'), ("You are a test design architect", designer),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(6):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        if pending(run)["gate"] == 3:
            break
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    assert "8 cases" in pending(run)["summary"]


def test_every_case_gets_a_test_across_batches_and_gaps_are_reported(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    ids = [f"REQ-{n:03d}" for n in range(1, 8)]  # 7 P1 requirements, 4 cases each, which the case budget allows (28 of 60)
    requirements = json.dumps({"requirements": [{"id": i, "title": "A", "statement": "add", "priority": "P1", "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"} for i in ids]})
    plan = json.dumps({"strategy": "Unit first", "areas": [{"id": "A1", "name": "Add", "requirement_ids": ids, "risk": "P1", "level": "Unit", "framework": "pytest", "rationale": "Pure logic"}], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}})
    kinds = ["Positive", "Negative", "Negative (Boundary)", "Exception"]

    def cases(text: str) -> str:
        wanted = re.findall(r'"id": "(REQ-\d+)"', text.rsplit("REQUIREMENTS:", 1)[-1].split("CASE QUOTA")[0])
        return json.dumps({"cases": [{"id": "x", "requirement_id": r, "scenario": f"{r} {kind}", "type": kind, "level": "Unit", "steps": ["call add"], "expected_result": "returns the sum 2", "oracle": "derived"} for r in wanted for kind in kinds]})

    numbers = []

    def author(text: str) -> str:
        wanted = re.findall(r'"id": "TC-APP-(\d+)"', text.rsplit("CASES:", 1)[-1].split("DETECTED RUNNERS")[0])
        retry = re.findall(r"TC-APP-(\d+)", text.rsplit("have no test yet", 1)[-1].split("CODE:")[0]) if "have no test yet" in text.rsplit("Generate executable", 1)[-1] else None
        chosen = retry if retry else wanted[:-1]  # the first reply always leaves one case out
        numbers.append(len(chosen))
        return json.dumps({"framework": "pytest", "files": [{"path": f"tests/agentic_qe/test_tc_app_{n}.py", "case_ids": [f"TC-APP-{n}"], "content": f"# CASE_ID: TC-APP-{n}\nfrom calc import add\n\n\ndef test_tc_app_{n}():\n    assert add(1, 1) == 2\n"} for n in chosen]})

    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", requirements), ("You are a principal test architect", plan),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'), ("You are a test design architect", cases), ("You are a test automation engineer", author),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(7):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        if pending(run)["gate"] == 4:
            break
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    assert "28 of 28 cases have tests" in pending(run)["summary"]
    assert sum(1 for n in numbers if n >= 4) == 3, "28 cases split into batches of 10"


def test_cases_a_batch_keeps_leaving_out_get_one_more_try(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    ids = [f"REQ-{n:03d}" for n in range(1, 8)]  # 7 P1 requirements, 4 cases each, which the case budget allows (28 of 60)
    requirements = json.dumps({"requirements": [{"id": i, "title": "A", "statement": "add", "priority": "P1", "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"} for i in ids]})
    plan = json.dumps({"strategy": "Unit first", "areas": [{"id": "A1", "name": "Add", "requirement_ids": ids, "risk": "P1", "level": "Unit", "framework": "pytest", "rationale": "Pure logic"}], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}})
    kinds = ["Positive", "Negative", "Negative (Boundary)", "Exception"]

    def cases(text: str) -> str:
        wanted = re.findall(r'"id": "(REQ-\d+)"', text.rsplit("REQUIREMENTS:", 1)[-1].split("CASE QUOTA")[0])
        return json.dumps({"cases": [{"id": "x", "requirement_id": r, "scenario": f"{r} {kind}", "type": kind, "level": "Unit", "steps": ["call add"], "expected_result": "returns the sum 2", "oracle": "derived"} for r in wanted for kind in kinds]})

    numbers = []

    def author(text: str) -> str:
        wanted = re.findall(r'"id": "TC-APP-(\d+)"', text.rsplit("CASES:", 1)[-1].split("DETECTED RUNNERS")[0])
        # a real run lost 9 of 60 cases with no error: however often it is asked, a full batch leaves its last case out
        chosen = re.findall(r"TC-APP-(\d+)", text.rsplit("have no test yet", 1)[-1].split("CODE:")[0])[:0] or (wanted[:-1] if len(wanted) > 5 else wanted)
        numbers.append(len(chosen))
        return json.dumps({"framework": "pytest", "files": [{"path": f"tests/agentic_qe/test_tc_app_{n}.py", "case_ids": [f"TC-APP-{n}"], "content": f"# CASE_ID: TC-APP-{n}\nfrom calc import add\n\n\ndef test_tc_app_{n}():\n    assert add(1, 1) == 2\n"} for n in chosen]})

    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", requirements), ("You are a principal test architect", plan),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'), ("You are a test design architect", cases), ("You are a test automation engineer", author),
    ]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(7):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        if pending(run)["gate"] == 4:
            break
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    assert "28 of 28 cases have tests" in pending(run)["summary"]
