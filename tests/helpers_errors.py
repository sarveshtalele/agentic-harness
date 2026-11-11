"""Shared helpers for the error and retry tests."""

import json

from backend.maf import llm

from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import GOOD_REVIEW, pending, upload_repo, wait_run


IDS = [f"REQ-{n:03d}" for n in range(1, 17)]  # 16 requirements make four design batches of four


REQUIREMENTS = json.dumps({"requirements": [{"id": i, "title": i, "statement": f"add behaves for {i}", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"} for i in IDS]})


PLAN = json.dumps({"strategy": "Unit first", "areas": [{"id": "A1", "name": "Add", "requirement_ids": IDS, "risk": "P0", "level": "Unit", "framework": "pytest", "rationale": "Pure logic"}], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}})


def cases_for(wanted):
    return json.dumps({"cases": [{"id": "TC-APP-001", "requirement_id": r, "scenario": f"{r} {k}", "type": k, "level": "Unit", "steps": ["call add"], "expected_result": "correct", "oracle": "specified"}
                                 for r in wanted for k in ["Positive", "Negative", "Negative (Boundary)", "Exception"]]})


class Designer:
    """Answers design requests. The batch holding REQ-013 gets a broken reply until healed."""

    def __init__(self, broken="I cannot produce that."):
        self.healed, self.broken, self.batches = False, broken, []

    def __call__(self, text):
        section = text.rsplit("Design test cases for only these requirements", 1)[-1].split("PLAN:")[0]
        wanted = [i for i in IDS if i in section]
        self.batches.append(wanted)
        return self.broken if "REQ-013" in wanted and not self.healed else cases_for(wanted)


def qe_client(designer):
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", REQUIREMENTS), ("You are a principal test architect", PLAN),
        *case_rules(), ("You are an independent reviewer", GOOD_REVIEW.replace("90", "95")), ("You are a test design architect", designer)]))


def run_to_design(client, project, designer):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    qe_client(designer)
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(4):
        run = wait_run(client, run["id"])
        if run["status"] != "waiting_approval":
            break
        client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    return wait_run(client, run["id"], ("waiting_approval", "failed", "completed"))
