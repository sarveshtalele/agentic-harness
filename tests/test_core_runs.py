"""JUnit parsing, runners, healing and traceability."""

import pytest

from backend.qe import execution, model, trace


JUNIT = '<testsuite><testcase classname="tests.test_a" name="test_TC_APP_001_ok" time="0.1"/><testcase classname="t" name="test_TC_APP_002" time="0"><failure message="boom">trace</failure></testcase><testcase classname="t" name="s"><skipped/></testcase></testsuite>'


def test_parse_junit_counts():
    result = execution.parse_junit(JUNIT)
    assert (result["total"], result["passed"], result["failed"], result["skipped"]) == (3, 1, 1, 1)
    assert "boom" in result["cases"][1]["message"]


def test_parse_junit_garbage_is_empty():
    assert execution.parse_junit("<not xml")["total"] == 0


@pytest.mark.parametrize(("failed", "passed", "code", "expected"), [(0, 0, 0, "INCONCLUSIVE"), (0, 3, None, "INCONCLUSIVE"), (1, 3, 1, "FAIL"), (0, 3, 1, "FAIL"), (0, 3, 0, "PASS")])
def test_verdict_never_passes_without_tests(failed, passed, code, expected):
    assert execution.verdict({"passed": passed, "failed": failed}, code) == expected


def test_real_pytest_run_and_env_scrubbed(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    (tmp_path / "test_env.py").write_text("import os\n\ndef test_clean():\n    assert 'OPENAI_API_KEY' not in os.environ\n\ndef test_fail():\n    assert 1 == 2\n")
    result = execution.run_suite("pytest", tmp_path, ".", tmp_path / "out")
    assert (result["passed"], result["failed"], result["verdict"]) == (1, 1, "FAIL")


def test_unregistered_runner_refused(tmp_path):
    assert execution.run_suite("rm", tmp_path, ".", tmp_path)["verdict"] == "INCONCLUSIVE"


@pytest.mark.parametrize(("old", "new", "ok"), [
    ("assert a == 1", "assert a == 1\nx = 2", True),
    ("assert a == 1", "assert True", False),
    ("assert a == 1", "x = 1", False),
    ("assert a == 1", "assert a == 2", False),
    ("def t():\n    assert a", "@pytest.mark.xfail\ndef t():\n    assert a", False),
])
def test_healing_cannot_weaken_assertions(old, new, ok):
    assert execution.assertions_preserved(old, new)[0] is ok


@pytest.mark.parametrize(("message", "expected"), [("ModuleNotFoundError: x", "ENVIRONMENT"), ("locator not found", "SELECTOR_DRIFT"), ("fixture 'db' not found", "FIXTURE_DRIFT"), ("assert 4 == 5", "DEFECT")])
def test_failure_classification(message, expected):
    assert execution.classify_failure(message) == expected


REQS = [{"id": "REQ-1", "title": "A", "priority": "P0"}, {"id": "REQ-2", "title": "B", "priority": "P2"}]


def test_coverage_gaps_and_duplicates():
    cases = [{"id": "TC-1", "requirement_id": "REQ-1", "type": "Positive", "scenario": "x"}, {"id": "TC-2", "requirement_id": "REQ-1", "type": "Positive", "scenario": "X "}]
    # REQ-2 (P2) has a budget here and no case: a gap since QE v2 (the design stage passes only budgeted requirements)
    assert model.coverage_gaps(REQS, cases) == ["REQ-1: needs 2 Negative cases", "REQ-2: no case"], "no error behaviour stated, so no Exception case is required"
    erring = [{**REQS[0], "error_behaviour": "raises ValueError when b is 0"}]
    assert model.coverage_gaps(erring, cases) == ["REQ-1: needs 2 Negative cases", "REQ-1: no Exception case, and the requirement states error behaviour"]
    assert model.coverage_gaps([{**REQS[0], "quote": "raise ValueError('b is 0')"}], cases)[-1].endswith("states error behaviour"), "a raise on the verified quote counts"
    assert model.duplicate_scenarios(cases) == ["TC-2"]


def test_plan_confidence_bands():
    good = {"areas": [{"requirement_ids": ["REQ-1"], "level": lv} for lv in ("Unit", "Integration", "E2E")]}
    assert model.plan_confidence(REQS, good)["verdict"] == "APPROVED"
    assert model.plan_confidence(REQS, {"areas": [{"requirement_ids": ["REQ-2"], "level": "Unit"}]})["verdict"] == "REJECTED"


def test_vague_expected_result_refused():
    with pytest.raises(ValueError):
        model.TestCase(id="T", requirement_id="R", scenario="s", type="Positive", level="Unit", steps=["a"], expected_result="works", oracle="specified")


def test_trace_matrix_and_release_verdict():
    cases = [{"id": "TC-APP-001", "requirement_id": "REQ-1", "type": "Positive", "level": "Unit"}, {"id": "TC-APP-002", "requirement_id": "REQ-1", "type": "Negative", "level": "Unit"}]
    tests = [{"case_id": "TC-APP-001", "path": "tests/a.py"}]
    suites = [execution.parse_junit(JUNIT)]
    matrix = trace.build_matrix(REQS, cases, tests, suites)
    assert matrix["rows"][0]["cases"][0]["result"] == "passed" and matrix["rows"][0]["cases"][1]["result"] == "failed"
    assert matrix["rows"][0]["covered"] and matrix["gaps"] == []
    assert trace.release_summary(matrix, suites, [])["verdict"] == "FAIL"


def test_release_without_execution_is_inconclusive():
    matrix = trace.build_matrix(REQS, [], [], [])
    assert trace.release_summary(matrix, [], [])["verdict"] == "INCONCLUSIVE"



def test_a_budgeted_lower_priority_requirement_with_no_case_is_a_gap():
    low = [{"id": "REQ-9", "priority": "P2", "statement": "x"}]
    assert model.coverage_gaps(low, []) == ["REQ-9: no case"]
    assert model.coverage_gaps(low, [{"requirement_id": "REQ-9", "type": "Positive"}]) == []
