"""Rubrics, totals and verdicts of per-case confidence."""

import pytest

from backend.qe import confidence
from tests.helpers_confidence import design_item, repo  # noqa: F401 - fixtures


# unit tests of the rubric, one per rule of the source


def test_each_rubric_sums_to_100_and_the_thresholds_are_the_plugins():
    assert {kind: sum(rubric.values()) for kind, rubric in confidence.RUBRIC.items()} == {"design": 100, "code": 100, "plan": 100}
    assert confidence.RUBRIC["design"] == {"source_proven": 30, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}
    assert confidence.RUBRIC["code"] == {"compilable": 30, "assertion_integrity": 30, "import_safety": 20, "traceability_present": 20}
    assert confidence.RUBRIC["plan"] == {"controls_covered": 40, "level_fit": 30, "scenarios_derivable": 30}
    assert (confidence.THRESHOLD, confidence.ASSERTION_FLOOR) == (70, 20)


@pytest.mark.parametrize("total,verdict", [(100, "APPROVED"), (99, "REVISE"), (70, "REVISE"), (69, "REJECT"), (0, "REJECT")])
def test_verdict_is_decided_by_code_from_the_total(total, verdict):
    assert confidence.verdict_for(total) == verdict


def test_a_perfect_verified_case_is_approved(repo):
    record = confidence.check_item(design_item(), "design", repo)
    assert (record["total"], record["verdict"], record["evidence"], record["low"], record["problems"]) == (100, "APPROVED", "verified", False, [])


def test_the_total_is_the_sum_of_the_scores_not_the_models_number(repo):
    item = design_item(scores={"source_proven": 20, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}, total=100, flaws=[{"dimension": "source_proven", "evidence": "calc.py:2", "fix": "Cite it"}])
    record = confidence.check_item(item, "design", repo)
    assert record["total"] == 90 and record["claimed_total"] == 100
    assert any("does not equal the sum" in p for p in record["problems"])


def test_an_invented_verdict_is_recomputed(repo):
    item = design_item(scores={"source_proven": 10, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}, total=80, verdict="APPROVED", flaws=[{"dimension": "source_proven", "evidence": "calc.py:2", "fix": "Cite it"}])
    record = confidence.check_item(item, "design", repo)
    assert record["verdict"] == "REVISE" and record["scored_verdict"] == "REVISE"
    assert any("verdict APPROVED does not follow the rule" in p for p in record["problems"])


@pytest.mark.parametrize("scores,fragment", [
    ({"source_proven": 31, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}, "source_proven must be a whole number from 0 to 30"),
    ({"source_proven": 29.5, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}, "source_proven must be a whole number"),
    ({"source_proven": -1, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}, "source_proven must be a whole number"),
    ({"source_proven": 30, "correct_target": 25, "expected_derivable": 25}, "fixture_validity must be a whole number"),
    ({"source_proven": 30, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20, "style": 5}, "unknown dimension style"),
])
def test_scores_must_be_whole_numbers_in_range_and_known(repo, scores, fragment):
    record = confidence.check_item(design_item(scores=scores, flaws=[{"dimension": "x", "evidence": "calc.py:2", "fix": "y"}]), "design", repo)
    assert any(fragment in p for p in record["problems"]), record["problems"]


def test_a_score_below_100_needs_flaws_with_path_line_evidence_and_a_fix(repo):
    scores = {"source_proven": 20, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}
    none = confidence.check_item(design_item(scores=scores, total=90, verdict="REVISE"), "design", repo)
    assert any("must name each flaw" in p for p in none["problems"])
    vague = confidence.check_item(design_item(scores=scores, total=90, verdict="REVISE", flaws=[{"dimension": "source_proven", "evidence": "somewhere in calc", "fix": ""}]), "design", repo)
    assert any("needs evidence as path:line and a fix" in p for p in vague["problems"])
    good = confidence.check_item(design_item(scores=scores, total=90, verdict="REVISE", flaws=[{"dimension": "source_proven", "evidence": "calc.py:2", "fix": "Cite the return line"}]), "design", repo)
    assert good["problems"] == [] and good["flaws"][0]["file"] == "calc.py" and good["flaws"][0]["line"] == 2


def test_a_missing_citation_is_a_reject_however_high_the_score(repo):
    record = confidence.check_item(design_item(component={"file": "invented.py", "line": 4, "symbol": "ghost"}), "design", repo)
    assert record["total"] == 100 and record["evidence"] == "missing" and record["verdict"] == "REJECT" and record["low"]
    assert "invented.py:4" in record["problems"][-1]


def test_a_flaw_citation_that_is_not_on_disk_is_a_reject(repo):
    scores = {"source_proven": 20, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20}
    record = confidence.check_item(design_item(scores=scores, total=90, verdict="REVISE", flaws=[{"dimension": "source_proven", "evidence": "gone.py:1", "fix": "x"}]), "design", repo)
    assert record["evidence"] == "missing" and record["verdict"] == "REJECT"


@pytest.mark.parametrize("path", ["../outside.py", "/etc/passwd", "sub/../../outside.py"])
def test_a_path_outside_the_repository_is_a_reject(repo, tmp_path, path):
    (tmp_path.parent / "outside.py").write_text("x = 1\n", encoding="utf-8")
    record = confidence.check_item(design_item(component={"file": path, "line": 1, "symbol": "x"}), "design", repo)
    assert record["evidence"] == "missing" and record["verdict"] == "REJECT"
    assert "outside the repository" in record["problems"][-1]


def test_a_symlink_that_leaves_the_repository_is_a_reject(repo, tmp_path):
    outside = tmp_path.parent / "secret_target.py"
    outside.write_text("x = 1\n", encoding="utf-8")
    try:
        (repo / "link.py").symlink_to(outside)
    except OSError:
        pytest.skip("this system cannot make symlinks")
    assert confidence.check_item(design_item(component={"file": "link.py", "line": 1, "symbol": "x"}), "design", repo)["verdict"] == "REJECT"


def test_a_line_beyond_the_end_of_the_file_is_a_reject(repo):
    assert confidence.check_item(design_item(component={"file": "calc.py", "line": 2, "symbol": "add"}), "design", repo)["evidence"] == "verified"
    for line in (3, 99):
        record = confidence.check_item(design_item(component={"file": "calc.py", "line": line, "symbol": "add"}), "design", repo)
        assert record["evidence"] == "missing" and record["verdict"] == "REJECT", line
    assert confidence.check_item(design_item(component={"file": "calc.py", "line": 0, "symbol": "add"}), "design", repo)["verdict"] == "REJECT"


def test_a_file_over_5_mb_does_not_count(repo):
    (repo / "huge.py").write_bytes(b"x = 1\n" * 1_000_000)
    assert (repo / "huge.py").stat().st_size > confidence.MAX_FILE_BYTES
    assert confidence.check_item(design_item(component={"file": "huge.py", "line": 1, "symbol": "x"}), "design", repo)["verdict"] == "REJECT"
