"""QE v2 step 3, item D: a Gate 3 send-back designs again only the requirements its feedback names."""
import json

from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.helpers_v2 import TWO, cases_json, start, to_gate
from tests.reviewing import auditor


TWO_REQS = json.dumps({"requirements": [
    {"id": "REQ-001", "title": "Add", "statement": "add returns the sum", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"},
    {"id": "REQ-002", "title": "Sub", "statement": "sub returns the difference", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 6, "quote": "return a - b"}]})
TWO_PLAN = json.dumps({"strategy": "Unit", "areas": [{"id": "A1", "name": "Arithmetic", "requirement_ids": ["REQ-001", "REQ-002"], "risk": "P0", "level": "Unit", "framework": "pytest", "rationale": "Logic"}],
                       "skipped_levels": {"Integration": "No IO in this library", "E2E": "No UI in this library"}})


def two_designs(text):
    asked = json.loads(text.split("REQUIREMENTS:\n", 1)[1].split("\nCASE QUOTA", 1)[0])
    tag = " v2" if "FEEDBACK:" in text else ""
    return cases_json(*[{"id": "TC-X", "requirement_id": r["id"], "scenario": f"{r['id']} {kind} {n}{tag}", "type": kind, "level": "Unit", "steps": ["call it"], "expected_result": "returns 5", "oracle": "derived", "test_data": "2, 3"}
                        for r in asked for n, kind in enumerate(("Positive", "Negative", "Negative (Boundary)", "Negative"))])


def marks(sc):
    count = lambda needle: sum(needle in call for call in sc.calls)
    return {"design": count("Design test cases for only these requirements"), "review": count("Review type: design cases."), "audit": count("Audit these designed cases.")}


def test_a_gate_3_send_back_designs_again_only_the_requirements_it_names(client, project):
    reviewed, audited = [], []  # `reviewed` stays empty: the review calls are counted by marks()
    sc, run = start(client, project, [("Design test cases for only these requirements", two_designs), ("Audit these designed cases.", auditor(lambda i, n: audited.append(i) or "COVERS"))],
                    repo=TWO, plan=TWO_PLAN, requirements=TWO_REQS)
    run, approval = to_gate(client, run, 3)
    first = marks(sc)
    assert first["design"] == 1 and len(run["state"]["cases"]) == 8 and len(audited) == 8
    before = {c["scenario"] for c in run["state"]["cases"] if c["requirement_id"] == "REQ-001"}
    calls_before = len(sc.calls)
    assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": False, "feedback": "REQ-002 subtraction cases are too shallow, design them again"}).status_code == 200
    run, approval = to_gate(client, run, 3)
    again = {k: v - first[k] for k, v in marks(sc).items()}
    cases = run["state"]["cases"]
    assert again["design"] == 1, "only REQ-002 is designed"
    asked = [call for call in sc.calls[calls_before:] if "Design test cases for only these requirements" in call]
    assert '"id": "REQ-002"' in asked[0].split("CASE QUOTA")[0] and '"id": "REQ-001"' not in asked[0].split("CASE QUOTA")[0]
    assert len(audited) == 8 + 4, "only the four new REQ-002 cases were audited again"
    assert again == {"design": 1, "review": 1, "audit": 1} and len(reviewed) == 0, "one design, one review and one audit call, for the four new cases only"
    assert {c["scenario"] for c in cases if c["requirement_id"] == "REQ-001"} == before, "REQ-001 keeps its cases"
    assert all(c["scenario"].endswith("v2") for c in cases if c["requirement_id"] == "REQ-002") and len(cases) == 8
    assert [c["id"] for c in cases] == [f"TC-APP-{n:03d}" for n in range(1, 9)]
    assert run["state"]["design_audit"]["counts"]["COVERS"] == 8 and run["state"]["design_audit"]["unaudited"] == []


def test_a_send_back_that_names_nothing_designs_everything_again(client, project):
    sc, run = start(client, project, [("Design test cases for only these requirements", two_designs)], repo=TWO, plan=TWO_PLAN, requirements=TWO_REQS)
    run, approval = to_gate(client, run, 3)
    assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": False, "feedback": "the negative cases are weak everywhere, design them again"}).status_code == 200
    run, approval = to_gate(client, run, 3)
    assert marks(sc)["design"] == 2 and all(c["scenario"].endswith("v2") for c in run["state"]["cases"])
