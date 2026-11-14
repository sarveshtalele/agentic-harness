"""Carry-forward hook: each seeded defect is blocked with the item named."""
import copy

from backend.qe import carry

REQ = [{"id": "REQ-001", "statement": "add", "priority": "P0", "file": "calc.py", "line": 2, "quote": "return a + b"},
       {"id": "REQ-004", "statement": "sub", "priority": "P1", "file": "calc.py", "line": 5, "quote": "return a - b"}]
PLAN = {"areas": [{"id": "A1", "name": "Math", "requirement_ids": ["REQ-001", "REQ-004"], "level": "Unit", "risk": "P0"}]}
CASES = [{"id": "TC-APP-001", "requirement_id": "REQ-001", "scenario": "adds", "level": "Unit", "steps": ["add(2,3)"], "expected_result": "5", "test_data": "2,3"},
         {"id": "TC-APP-002", "requirement_id": "REQ-004", "scenario": "subs", "level": "Unit", "steps": ["sub(3,2)"], "expected_result": "1", "test_data": "3,2"}]
TESTS = [{"case_id": "TC-APP-001", "path": "tests/t1.py"}, {"case_id": "TC-APP-002", "path": "tests/t2.py"}]


def state(**kw):
    return copy.deepcopy({"requirements": REQ, "plan": PLAN, "cases": CASES, "tests": TESTS, **kw})


def approved(**kw):
    return {"trace": {"approved": carry.snapshot(state(**kw))}}


def test_before_blocks_requirement_quote_edited_after_gate_1():
    s = {"requirements": copy.deepcopy(REQ), "trace": {"approved": carry.snapshot({"requirements": REQ})}}
    s["requirements"][1]["quote"] = "return a - b + 1"
    bad = carry.before("plan", s)
    assert len(bad) == 1 and bad[0].startswith("REQ-004 changed after Gate 1")


def test_before_blocks_missing_approved_item_and_passes_clean():
    s = {"requirements": copy.deepcopy(REQ), "trace": {"approved": carry.snapshot({"requirements": REQ})}}
    assert carry.before("plan", s) == []
    s["requirements"].pop(0)
    assert "requirement REQ-001 is missing before plan" in carry.before("plan", s)[0]


def test_before_lets_a_stage_regenerate_its_own_output():
    s = {**state(), **approved(), "cases": []}
    s["trace"]["approved"].pop("case"), s["trace"]["approved"].pop("test")
    s["cases"] = [{**CASES[0], "expected_result": "6"}]  # design after a Gate 3 send-back replaces the cases
    assert carry.before("design", s) == []


def test_after_blocks_case_expected_result_altered_during_generate():
    old, new = state(), state()
    new["cases"][1]["expected_result"] = "2"
    bad, report = carry.after("generate", old, new)
    assert len(bad) == 1 and bad[0].startswith("TC-APP-002 changed by generate (expected_result)")
    assert report["changed"] == 1 and report["verdict"] == "BLOCKED"


def test_after_blocks_requirement_dropped_by_plan_without_reason():
    old = {"requirements": copy.deepcopy(REQ)}
    new = {**old, "plan": {"areas": [{"id": "A1", "name": "Math", "requirement_ids": ["REQ-001"], "level": "Unit", "risk": "P0"}]}}
    bad, report = carry.after("plan", old, new)
    assert len(bad) == 1 and "requirement REQ-004 has no plan scenario in plan and no written reason" in bad[0]
    assert report["dropped_without_reason"] == 1


def test_after_blocks_invented_requirement_case_and_test_ids():
    bad, _ = carry.after("plan", {"requirements": REQ}, {"requirements": REQ, "plan": {"areas": [{"id": "A1", "requirement_ids": ["REQ-001", "REQ-004", "REQ-099"], "level": "Unit"}]}})
    assert any("REQ-099" in b and "does not exist" in b for b in bad)
    new = state()
    new["cases"].append({**CASES[0], "id": "TC-APP-003", "requirement_id": "REQ-777"})
    bad, _ = carry.after("design", {"requirements": REQ, "plan": PLAN}, new)
    assert any("TC-APP-003" in b and "REQ-777" in b for b in bad)
    new = state()
    new["tests"].append({"case_id": "TC-APP-042", "path": "tests/t42.py"})
    bad, _ = carry.after("generate", state(tests=[]), new)
    assert any("TC-APP-042" in b and "does not exist" in b for b in bad)


def test_after_clean_pass_counts_everything_carried():
    bad, report = carry.after("generate", state(tests=[]), state())
    assert bad == [] and report["verdict"] == "PASS"
    assert (report["upstream"], report["carried"], report["changed"], report["new"]) == (5, 5, 0, 2)
    assert "5 upstream items carried 5" in carry.summary(report)


def test_after_passes_when_the_stage_gives_a_reason():
    old = {"requirements": REQ, "plan": PLAN}
    new = {**old, "cases": CASES[:1], "case_limit": {"notice": True, "left_out_requirements": ["REQ-004"], "message": "budget"}}
    bad, report = carry.after("design", old, new)
    assert bad == [] and report["dropped_with_reason"] == 1 and report["dropped_without_reason"] == 0
    bad, _ = carry.after("generate", state(tests=[]), state(tests=TESTS[:1], tests_missing=["TC-APP-002"]))
    assert bad == []
    bad, _ = carry.after("design", old, {**old, "cases": CASES[:1]})
    assert len(bad) == 1 and "REQ-004" in bad[0]


def test_plan_may_leave_out_a_lower_priority_requirement_and_says_so():
    low = [*copy.deepcopy(REQ), {"id": "REQ-009", "statement": "log", "priority": "P2", "file": "calc.py", "line": 9, "quote": "log(x)"}]
    bad, report = carry.after("plan", {"requirements": low}, {"requirements": low, "plan": copy.deepcopy(PLAN)})
    assert bad == [] and report["dropped_with_reason"] == 1 and report["dropped_without_reason"] == 0
