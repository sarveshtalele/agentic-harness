"""Send-back of rejected cases and review batches."""

import json

from tests.helpers_api import pending
from tests.helpers_confidence import base_rules, go_to_gate


def test_a_rejected_case_goes_back_alone_with_its_flaws_and_the_others_are_untouched(client, project):
    seen, rewrites = [], []
    state = {"first": True}

    def grade(kind, key):
        if kind == "design" and key == "C2" and state["first"]:
            state["first"] = False
            return {"scores": {"source_proven": 5, "correct_target": 10, "expected_derivable": 10, "fixture_validity": 5}, "flaws": [{"dimension": "source_proven", "evidence": "calc.py:2", "fix": "Name the add function and assert 0 for add(-1, 1)"}]}
        return None

    def rewrite(text):
        rewrites.append(text)
        return json.dumps({"cases": [{"id": "x", "requirement_id": "REQ-001", "scenario": "Opposites cancel", "type": "Negative", "level": "Unit", "steps": ["call add(-1,1)"], "expected_result": "returns 0", "oracle": "derived"}]})

    run, scripted = go_to_gate(client, project, 3, base_rules(grade=grade, seen=seen, extra=[("Rewrite only this one test case", rewrite)]))
    assert len(rewrites) == 1, "only the rejected case is sent back"
    sent = rewrites[0].rsplit("Rewrite only this one test case", 1)[-1]
    assert "Negatives" in sent and "Name the add function and assert 0" in sent and "calc.py:2" in sent, "its flaw, evidence and fix go with it"
    assert all(other not in sent for other in ("Adds", "Zero", "Bad type")), "no other case is sent"
    first, second = [s for s in seen if s[0] == "design"]
    assert first[1] == ["C1", "C2", "C3", "C4"] and second[1] == ["C2"], "only the sent-back case is reviewed again"
    gate = pending(run)
    records = {r["tc_id"]: r for r in gate["payload"]["confidence"]["records"]}
    assert records["TC-APP-002"]["round"] == 2 and records["TC-APP-002"]["first_round"]["verdict"] == "REJECT" and records["TC-APP-002"]["verdict"] == "APPROVED"
    assert [records[i]["round"] for i in ("TC-APP-001", "TC-APP-003", "TC-APP-004")] == [1, 1, 1]
    doc = next(d for d in client.get(f"/api/projects/{project['id']}/documents").json() if d["kind"] == "test_cases")
    cases = {c["id"]: c for c in client.get(f"/api/documents/{doc['id']}").json()["data"]}
    assert cases["TC-APP-002"]["scenario"] == "Opposites cancel" and cases["TC-APP-001"]["scenario"] == "Adds" and cases["TC-APP-004"]["scenario"] == "Bad type"
    tokens = gate["payload"]["confidence"]["tokens"]
    assert tokens["revise"] > 0 and tokens["review"] > 0 and tokens["total"] == tokens["review"] + tokens["revise"], "real token use is reported"


def test_a_revise_is_not_sent_back_only_a_reject(client, project):
    seen, rewrites = [], []
    revise_only = lambda kind, key: {"scores": {"fixture_validity": 10}} if kind == "design" and key == "C2" else None
    run, _ = go_to_gate(client, project, 3, base_rules(grade=revise_only, seen=seen, extra=[("Rewrite only this one test case", lambda t: rewrites.append(t) or "x")]))
    assert rewrites == [] and len([s for s in seen if s[0] == "design"]) == 1
    records = {r["tc_id"]: r for r in pending(run)["payload"]["confidence"]["records"]}
    assert records["TC-APP-002"]["verdict"] == "REVISE" and records["TC-APP-002"]["total"] == 90


def test_only_one_round_and_a_case_that_stays_rejected_stays_visible(client, project):
    seen, rewrites = [], []

    def rewrite(text):
        rewrites.append(text)
        return json.dumps({"cases": [{"id": "x", "requirement_id": "REQ-001", "scenario": "Still weak", "type": "Negative", "level": "Unit", "steps": ["call add(-1,1)"], "expected_result": "returns 0", "oracle": "derived"}]})

    always = lambda kind, key: {"scores": {"source_proven": 5, "correct_target": 10, "expected_derivable": 10, "fixture_validity": 5}} if kind == "design" and key == "C2" else None
    run, _ = go_to_gate(client, project, 3, base_rules(grade=always, seen=seen, extra=[("Rewrite only this one test case", rewrite)]))
    assert len(rewrites) == 1 and len([s for s in seen if s[0] == "design"]) == 2, "one send-back and one second review, never a third"
    payload = pending(run)["payload"]["confidence"]
    stuck = next(r for r in payload["records"] if r["tc_id"] == "TC-APP-002")
    assert stuck["verdict"] == "REJECT" and stuck["round"] == 2 and stuck["first_round"]["verdict"] == "REJECT" and stuck["flaws"]
    assert payload["verdict"] == "REJECT" and payload["counts"]["reject"] == 1, "the roll-up shows it, nothing is hidden"


def test_approving_a_reject_needs_a_reason_that_reaches_the_ledger_and_a_revise_does_not(client, project):
    seen = []
    always = lambda kind, key: {"scores": {"source_proven": 5, "correct_target": 10, "expected_derivable": 10, "fixture_validity": 5}} if kind == "design" and key == "C2" else ({"scores": {"fixture_validity": 10}} if kind == "design" and key == "C3" else None)
    run, _ = go_to_gate(client, project, 3, base_rules(grade=always, seen=seen, extra=[("Rewrite only this one test case", lambda t: "I cannot")]))
    gate = pending(run)
    assert {r["tc_id"]: r["verdict"] for r in gate["payload"]["confidence"]["records"]}["TC-APP-003"] == "REVISE"
    for blank in ("", "   "):
        refused = client.post(f"/api/approvals/{gate['id']}/decide", json={"approved": True, "feedback": blank})
        assert refused.status_code == 400 and "TC-APP-002" in refused.text and "reason" in refused.text.lower()
    assert next(g for g in client.get(f"/api/projects/{project['id']}/gates").json() if g["gate"] == 3)["status"] == "pending"
    assert client.post(f"/api/approvals/{gate['id']}/decide", json={"approved": True, "feedback": "Boundary covered by TC-APP-003"}).status_code == 200
    entries = client.get(f"/api/projects/{project['id']}/ledger").json()
    accepted = next(e for e in entries["entries"] if e["action"] == "gate.reject_accepted")
    assert "Boundary covered by TC-APP-003" in accepted["data"] and "TC-APP-002" in accepted["data"] and accepted["target"] == "G3"
    assert entries["verification"]["valid"]


def test_a_gate_with_only_revise_items_needs_no_reason(client, project):
    revise = lambda kind, key: {"scores": {"fixture_validity": 10}} if kind == "design" else None
    run, _ = go_to_gate(client, project, 3, base_rules(grade=revise))
    assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True}).status_code == 200


def test_a_review_batch_that_cannot_be_read_is_not_run_and_never_a_pass(client, project):
    run, _ = go_to_gate(client, project, 3, base_rules(extra=[("Review type: design cases.", "I think these cases look fine, 95 out of 100.")]))
    review = pending(run)["payload"]["confidence"]
    assert review["verdict"] == "NOT RUN" and review["score"] is None and review["counts"]["not_run"] == 4
    assert all(r["status"] == "NOT RUN" and r["total"] is None and r["verdict"] != "APPROVED" for r in review["records"])
    assert run["status"] == "waiting_approval", "the stage went on to its gate"
    assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True}).status_code == 200, "NOT RUN is not a REJECT, so a person may go on"


def test_one_case_the_reviewer_skipped_is_not_run_and_the_roll_up_is_not_approved(client, project):
    skip = lambda kind, key: {"skip": True} if kind == "design" and key == "C3" else None
    run, _ = go_to_gate(client, project, 3, base_rules(grade=skip))
    review = pending(run)["payload"]["confidence"]
    by_id = {r["tc_id"]: r for r in review["records"]}
    assert by_id["TC-APP-003"]["status"] == "NOT RUN" and by_id["TC-APP-003"]["total"] is None
    assert review["verdict"] == "REVISE" and review["score"] == 100 and review["counts"]["not_run"] == 1


def test_an_invented_citation_makes_the_case_a_reject_on_the_gate(client, project):
    def invented(kind, key):
        if kind == "design" and key == "C1":
            return {"component": {"file": "ghost.py", "line": 9, "symbol": "ghost"}}
        return None

    run, _ = go_to_gate(client, project, 3, base_rules(grade=invented, extra=[("Rewrite only this one test case", lambda t: "I cannot")]))
    first = next(r for r in pending(run)["payload"]["confidence"]["records"] if r["tc_id"] == "TC-APP-001")
    assert first["total"] == 100 and first["verdict"] == "REJECT" and first["evidence"] == "missing"
