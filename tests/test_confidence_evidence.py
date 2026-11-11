"""Evidence checks, weak assertions and record types."""

import pytest

from backend.qe import confidence
from tests import reviewing
from tests.helpers_confidence import design_item, repo  # noqa: F401 - fixtures


def code_item(**change):
    item = {"tc_id": "TC-1", "file": "calc.py", "scores": dict(reviewing.PERFECT["code"]), "total": 100, "verdict": "APPROVED", "flaws": []}
    return {**item, **change}


def test_a_design_case_without_its_component_is_a_reject(repo):
    record = confidence.check_item(design_item(component=None), "design", repo)
    assert record["verdict"] == "REJECT" and any("component under test" in p for p in record["problems"])


def test_without_a_repository_the_evidence_is_not_checked_and_never_called_verified(tmp_path):
    record = confidence.check_item(design_item(), "design", tmp_path / "does-not-exist")
    assert record["evidence"] == "not-checked" and record["verdict"] == "APPROVED"
    assert confidence.check_item(design_item(), "design", None)["evidence"] == "not-checked"


def test_not_strict_reports_not_checked_for_a_missing_citation(repo):
    record = confidence.check_item(design_item(component={"file": "invented.py", "line": 4, "symbol": "ghost"}), "design", repo, strict=False)
    assert record["evidence"] == "not-checked" and record["verdict"] == "APPROVED"


@pytest.mark.parametrize("assertion,low", [(30, False), (20, False), (19, True), (0, True)])
def test_weak_assertions_are_low_confidence_at_any_total(repo, assertion, low):
    scores = {"compilable": 30, "assertion_integrity": assertion, "import_safety": 20, "traceability_present": 20}
    total = sum(scores.values())
    flaws = [] if total == 100 else [{"dimension": "assertion_integrity", "evidence": "calc.py:2", "fix": "Assert the sum"}]
    record = confidence.check_item(code_item(scores=scores, total=total, verdict=confidence.verdict_for(total), flaws=flaws), "code", repo)
    assert record["low"] is low
    if assertion == 19:
        assert record["total"] == 89 and record["verdict"] == "REVISE" and "assertion integrity 19/30" in record["low_reason"]


def test_a_test_that_asserts_nothing_is_low_even_when_the_rest_is_perfect(repo):
    scores = {"compilable": 30, "assertion_integrity": 5, "import_safety": 20, "traceability_present": 20}
    record = confidence.check_item(code_item(scores=scores, total=75, verdict="REVISE", flaws=[{"dimension": "assertion_integrity", "evidence": "calc.py:1", "fix": "Assert the sum"}]), "code", repo)
    assert record["total"] == 75 and record["verdict"] == "REVISE" and record["low"] and "may pass without proving" in record["low_reason"]


def test_a_total_under_the_threshold_is_low(repo):
    scores = {"source_proven": 10, "correct_target": 25, "expected_derivable": 20, "fixture_validity": 10}
    record = confidence.check_item(design_item(scores=scores, total=65, verdict="REJECT", flaws=[{"dimension": "source_proven", "evidence": "calc.py:2", "fix": "x"}]), "design", repo)
    assert record["verdict"] == "REJECT" and record["low"]


def test_a_dimension_of_another_review_type_is_unknown(repo):
    assert confidence.check_item(design_item(scores={**reviewing.PERFECT["design"], "assertion_integrity": 0}), "design", repo)["problems"][0] == "unknown dimension assertion_integrity"


def test_a_code_record_without_its_test_file_is_a_reject(repo):
    assert confidence.check_item(code_item(file=""), "code", repo)["verdict"] == "REJECT"


def test_a_plan_record_uses_the_plan_dimensions(repo):
    record = confidence.check_item({"tc_id": "PLAN", "scores": dict(reviewing.PERFECT["plan"]), "total": 100, "verdict": "APPROVED"}, "plan", repo)
    assert record["total"] == 100 and record["verdict"] == "APPROVED" and record["evidence"] == "verified"


def test_check_doc_summarises_by_the_worst_rule_and_counts_what_did_not_run(repo):
    review = {"items": [design_item(tc_id="A"), design_item(tc_id="B", component={"file": "gone.py", "line": 1, "symbol": "x"})]}
    done = confidence.check_doc(review, "design", repo)
    summary = done["summary"]
    assert summary["verdict"] == "REJECT" and summary["counts"]["reject"] == 1 and summary["counts"]["evidence_missing"] == 1 and summary["score"] == 100
    only_good = confidence.summarise([confidence.check_item(design_item(), "design", repo)])
    assert only_good["verdict"] == "APPROVED"
    with_gap = confidence.summarise([confidence.check_item(design_item(), "design", repo), confidence.not_run("X", "design", "reply broke")])
    assert with_gap["verdict"] == "REVISE" and with_gap["counts"]["not_run"] == 1, "a case that did not run can never leave the roll-up APPROVED"
    nothing = confidence.summarise([confidence.not_run("X", "design", "reply broke")])
    assert nothing["verdict"] == "NOT RUN" and nothing["score"] is None


def test_a_failed_test_is_capped_after_execution(repo):
    ok = confidence.check_item(code_item(tc_id="TC-1", scores={**reviewing.PERFECT["code"], "import_safety": 15}, total=95, verdict="REVISE", flaws=[{"dimension": "import_safety", "evidence": "calc.py:1", "fix": "x"}]), "code", repo)
    other = {**ok, "tc_id": "TC-2"}
    after = confidence.cap_failed([ok, other], {"TC-1": "failed", "TC-2": "passed"})
    first, second = after["records"]
    assert (first["total"], first["total_before"], first["capped"], first["verdict"], first["low"]) == (60, 95, True, "REJECT", True)
    assert (second["total"], second["capped"], second["verdict"]) == (95, False, "REVISE")
    assert (after["score_before"], after["score"], after["capped"], after["failed"], after["executed"]) == (95, 78, 1, 1, 2)
    assert confidence.cap_failed([ok], {"TC-1": "not run"})["capped"] == 0, "a test that did not run is not capped, it is simply not run"


def test_a_total_already_under_the_cap_is_not_raised(repo):
    low = confidence.check_item(code_item(scores={"compilable": 10, "assertion_integrity": 10, "import_safety": 10, "traceability_present": 10}, total=40, verdict="REJECT", flaws=[{"dimension": "compilable", "evidence": "calc.py:1", "fix": "x"}]), "code", repo)
    assert confidence.cap_failed([low], {"TC-1": "failed"})["records"][0]["total"] == 40
