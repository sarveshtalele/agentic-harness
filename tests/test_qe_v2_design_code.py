"""QE v2 step 3: the oracle check in Design (V2), the code audit at Gate 4 (V1), planned levels, and a Gate 3 send-back that redesigns only what it names.

Everything runs through the real API with a scripted model; the checks themselves are real code.
"""
import json

from backend.config import project_dir
from backend.qe import model, oracle, plugin_bridge
from tests.helpers_api import CASES, PLAN, _test_file, client, project  # noqa: F401 - fixtures
from tests.helpers_v2 import case, cases_json, start, to_gate
from tests.reviewing import code_auditor

# ---- A: the oracle check, unit level ----

REQ = {"id": "REQ-001", "statement": "add returns the sum", "quote": "return a + b", "file": "calc.py", "line": 2}
RAISING = {"id": "REQ-002", "statement": "negative amounts are refused", "quote": "raise ValueError('negative amount')", "file": "pay.py", "line": 3}


def test_an_invented_expected_value_is_refused_and_a_stated_one_is_not():
    # the seeded invention: the quote says "return a + b", the case claims 42
    assert oracle.invented_values(case(expected_result="returns 42"), REQ, "") == ["42"], "a stated oracle needs the number in the quote or the code"
    assert oracle.invented_values(case(expected_result="returns 'Insufficient funds'"), REQ, "") == ["Insufficient funds"]
    assert oracle.invented_values(case(expected_result="raises KeyError"), REQ, "") == ["KeyError"]
    assert oracle.invented_values(case(expected_result="responds with status 404"), REQ, "") == ["404"]
    assert oracle.invented_values(case(expected_result="returns 5", oracle="derived"), REQ, "") == [], "a computed result need not appear as text"
    assert oracle.invented_values(case(expected_result="returns 42", oracle="derived"), REQ, "") == [], "derived: plain numbers are computed from the inputs"
    assert oracle.invented_values(case(expected_result="raises KeyError", oracle="derived"), REQ, "") == [], "derived: a builtin exception is allowed"
    assert oracle.invented_values(case(expected_result="raises ValueError with 'negative amount'"), RAISING, "") == [], "both values are in the quote"
    assert oracle.invented_values(case(expected_result="returns 42"), REQ, "if x == 42:\n    return 42") == [], "the code near the citation may state it"
    assert oracle.invented_values(case(expected_result="returns 42"), {**REQ, "quote": ""}, "") == [], "no quote, nothing to derive from"


def test_a_derived_case_may_not_invent_text_or_a_custom_exception():
    assert oracle.invented_values(case(expected_result="raises InsufficientFundsError", oracle="derived"), REQ, "") == ["InsufficientFundsError"]
    assert oracle.invented_values(case(expected_result="raises TypeError", oracle="derived"), REQ, "") == []
    assert oracle.invented_values(case(expected_result="returns 'nope'", oracle="derived"), REQ, "") == ["nope"]


# ---- A: through Design ----

def invented_set():
    first = json.loads(CASES)["cases"]
    first[0]["oracle"], first[0]["expected_result"] = "specified", "returns 42"
    return cases_json(*first)


def fixer(still_invented):
    fixed = json.loads(CASES)["cases"][0]
    if still_invented:
        fixed["oracle"], fixed["expected_result"] = "specified", "returns 42"
    return cases_json(fixed)


def test_design_redesigns_a_case_with_an_invented_value_once(client, project):
    messages = []
    sc, run = start(client, project, [("Rewrite only this one test case", lambda text: messages.append(text) or fixer(False))], cases=invented_set())
    run, approval = to_gate(client, run, 3)
    audit = approval["payload"]["design_audit"]
    assert audit["oracle_refused"] == 1 and audit["oracle_still"] == [] and audit["counts"]["COVERS"] == 4, audit
    assert len(messages) == 1 and "'42'" in messages[0] and "THE REVIEW SAID" in messages[0], "the fix message names the value and goes to the redesign"
    assert next(c for c in run["state"]["cases"] if c["id"] == "TC-APP-001")["expected_result"] == "returns 5"
    assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200


def test_a_case_still_inventing_after_the_redesign_is_a_reject_a_person_must_answer(client, project):
    sc, run = start(client, project, [("Rewrite only this one test case", lambda text: fixer(True))], cases=invented_set())
    run, approval = to_gate(client, run, 3)
    assert approval["payload"]["design_audit"]["oracle_still"] == ["TC-APP-001"]
    records = {r["tc_id"]: r for r in approval["payload"]["confidence"]["records"]}
    assert records["TC-APP-001"]["verdict"] == "REJECT" and any(f["dimension"] == "oracle" for f in records["TC-APP-001"]["flaws"])
    refused = client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True})
    assert refused.status_code == 400 and "TC-APP-001" in refused.text, refused.text


# ---- C: planned levels ----

def test_planned_levels_and_the_gap_check_and_the_quota_swap():
    plan = {"areas": [{"id": "A1", "level": "Unit", "requirement_ids": ["REQ-001"]}, {"id": "A2", "level": "Integration", "requirement_ids": ["REQ-001", "REQ-002"]}, {"id": "A3", "level": "Unit", "requirement_ids": ["REQ-002"]}]}
    levels = model.planned_levels(plan)
    assert levels == {"REQ-001": ["Unit", "Integration"], "REQ-002": ["Integration", "Unit"]}
    reqs = [{"id": "REQ-001", "priority": "P0"}, {"id": "REQ-002", "priority": "P2"}]
    unit = [case(id=f"C{i}", type=t) for i, t in enumerate(["Positive", "Negative", "Negative", "Negative"])]
    assert model.level_gaps(reqs, unit, levels, {"REQ-001": 4, "REQ-002": 1}) == ["REQ-001: no case at planned level Integration"]
    assert model.level_gaps(reqs, unit, levels, {"REQ-001": 1, "REQ-002": 1}) == [], "a quota of 1 covers one level"
    mixed = [*unit, case(id="C9", type="Negative", level="Integration")]
    kept, dropped = model.apply_quota(mixed, {"REQ-001": 4}, reqs[:1], levels)
    assert {c["level"] for c in kept} == {"Unit", "Integration"} and len(kept) == 4 and [c["id"] for c in dropped] == ["C3"], (kept, dropped)
    assert any(c["type"] == "Positive" for c in kept), "the swap never takes the only Positive"
    plain, _ = model.apply_quota(mixed, {"REQ-001": 4}, reqs[:1])
    assert {c["level"] for c in plain} == {"Unit"}, "without the planned levels the quota would have cut the Integration case"


def test_design_is_told_the_planned_levels_and_a_missing_level_is_a_gap_the_revision_fixes(client, project):
    plan = json.dumps({"strategy": "Both", "areas": [
        {"id": "A1", "name": "Add", "requirement_ids": ["REQ-001"], "risk": "P0", "level": "Unit", "framework": "pytest", "rationale": "Logic"},
        {"id": "A2", "name": "Add flow", "requirement_ids": ["REQ-001"], "risk": "P0", "level": "Integration", "framework": "pytest", "rationale": "Wiring"}], "skipped_levels": {"E2E": "No UI in this library"}})
    asked = []
    unit = json.loads(CASES)["cases"]
    both = [*unit[:3], {**unit[3], "scenario": "Another zero", "type": "Negative"}, {**unit[3], "scenario": "Wired", "type": "Negative", "level": "Integration", "oracle": "derived"}]

    def design(text):
        asked.append(text)
        return cases_json(*both) if "no case at planned level Integration" in text else CASES

    sc, run = start(client, project, [("Design test cases for only these requirements", design)], plan=plan)
    run, approval = to_gate(client, run, 3)
    assert "PLANNED LEVELS" in asked[0] and "REQ-001: Unit and Integration" in asked[0]
    assert len(asked) == 2 and "REQ-001: no case at planned level Integration" in asked[1], "the existing gap revision asked for it"
    assert sorted(c["level"] for c in run["state"]["cases"]).count("Integration") == 1 and run["state"]["design_gaps"] == [], run["state"]["design_gaps"]
    scenario = plugin_bridge.scenario_id("A2")
    gaps = " ".join(approval["payload"]["plugin_check"]["gaps"])
    assert scenario not in gaps, f"the Integration scenario {scenario} has a case: {gaps}"


# ---- B: the code audit (V1) at Gate 4 ----

def rewrite(text):
    assert "coverage audit (V1)" in text and "misses its case" in text, "the auditor's reason goes to the test author"
    return json.dumps({"framework": "pytest", "files": [_test_file(2, "assert add(-1, 1) == 0\n    assert add(5, -5) == 0")]})


def test_a_test_the_auditor_says_misses_is_rewritten_once_and_passes_v1(client, project):
    sc, run = start(client, project, [("Rewrite only this generated test file and fix every problem the coverage audit", rewrite)],
                    code_audit=code_auditor(lambda i, n: "MISSES" if i == "TC-APP-002" and n == 1 else "COVERS"))
    run, approval = to_gate(client, run, 4)
    validation = approval["payload"]["validation"]
    assert validation["audit"]["first"]["MISSES"] == 1 and validation["audit"]["regenerated"] == 1 and validation["audit"]["now"]["MISSES"] == 0, validation["audit"]
    assert validation["counts"]["V1"] == 0 and validation["counts"]["valid"] == 4 and "V1 0," in approval["summary"]
    root = project_dir(project["id"]) / "docs" / "qe" / plugin_bridge.app_name(project["id"]) / "05-generation"
    recorded = json.loads((root / "audit.json").read_text())
    assert recorded["_capture"]["agent_type"] == "coverage-auditor" and recorded["kind"] == "code" and {v["id"] for v in recorded["verdicts"]} == {f"TC-APP-00{n}" for n in range(1, 5)}
    confidence = json.loads((root / "confidence.json").read_text())
    assert confidence["_capture"]["agent_type"] == "confidence-reviewer" and len(confidence["items"]) == 4
    assert "add(5, -5)" in (project_dir(project["id"]) / "worktrees" / run["id"] / "tests/agentic_qe/test_tc_app_002.py").read_text()
    gaps = " ".join(validation["plugin_check"]["gaps"])
    assert "audit.json" not in gaps and "confidence.json" not in gaps and "no code confidence review" not in gaps, gaps


def test_a_test_that_still_misses_goes_to_needs_review_with_check_v1(client, project):
    sc, run = start(client, project, [], code_audit=code_auditor(lambda i, n: "MISSES" if i == "TC-APP-002" else "COVERS"))
    run, approval = to_gate(client, run, 4)
    validation = approval["payload"]["validation"]
    assert validation["counts"]["V1"] == 1 and validation["counts"]["valid"] == 3 and validation["invalid"] == ["tests/agentic_qe/test_tc_app_002.py"]
    row = next(t for t in validation["tests"] if t["case_id"] == "TC-APP-002")
    assert row["checks"]["V1"]["status"] == "FAIL" and "misses its case" in row["checks"]["V1"]["message"] and not row["valid"]
    assert "V1 1," in approval["summary"] and "3 of 4 tests valid" in approval["summary"]
    assert any("TC-APP-002 (MISSES)" in g for g in validation["plugin_check"]["gaps"]), "the plugin's own check agrees"


def test_a_test_the_auditor_never_answered_is_not_checked_not_passed(client, project):
    sc, run = start(client, project, [("Audit these generated tests.", lambda text: "not json")])
    run, approval = to_gate(client, run, 4)
    validation = approval["payload"]["validation"]
    assert {t["checks"]["V1"]["status"] for t in validation["tests"]} == {"NOT CHECKED"} and validation["counts"]["V1"] == 0
    assert validation["counts"]["valid"] == 4, "an auditor outage does not void tests; the card says NOT CHECKED"
