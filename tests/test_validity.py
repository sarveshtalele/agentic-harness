"""Validity checks V3 to V6 on real files in a real worktree, with a real pytest collect in a run environment. Nothing is mocked."""
import pytest

from backend.qe import validity
from tests.helpers_validity import CASES, GOOD, make_run_env


@pytest.fixture(scope="module")
def worktree(tmp_path_factory):
    root = tmp_path_factory.mktemp("run") / "wt"
    (root / "tests/agentic_qe").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "conftest.py").write_text("", encoding="utf-8")
    (root / "app/__init__.py").write_text("", encoding="utf-8")
    make_run_env(root)
    return root


def run_checks(worktree, code, case="TC-APP-001"):
    path = "tests/agentic_qe/test_x.py"
    (worktree / path).write_text(code, encoding="utf-8")
    return validity.check_file(worktree, path, code, [case], CASES)


def failed(checks):
    return {k for k, v in checks.items() if v["status"] == "FAIL"}


def test_a_good_test_passes_all_four_checks(worktree):
    checks = run_checks(worktree, GOOD)
    assert {k: v["status"] for k, v in checks.items()} == {"V2b": "PASS", "V3": "PASS", "V4": "PASS", "V5": "PASS", "V6": "PASS"}, checks
    assert "collected 1 test" in checks["V3"]["message"]


@pytest.mark.parametrize("body, message", [
    ("def test_a():\n    result = add(2, 3)\n", "no assertion"),
    ("def test_a():\n    assert True\n", "tautology"),
    ("def test_a():\n    assert add(2, 3) == add(2, 3)\n", "tautology"),
    ("def test_a():\n    assert 1\n", "tautology"),
    ("@pytest.mark.skip(reason='later')\ndef test_a():\n    assert add(2, 3) == 5\n", "skip"),
    ("def test_a():\n    pytest.skip('no')\n    assert add(2, 3) == 5\n", "skip"),
    ("@pytest.mark.xfail\ndef test_a():\n    assert add(2, 3) == 5\n", "xfail"),
    ("def test_a():\n    assert add(2, 3) == 4\n", "expected result"),
])
def test_v5_refuses_weak_assertions_and_names_the_check(worktree, body, message):
    checks = run_checks(worktree, f"# CASE_ID: TC-APP-001\nimport pytest\nfrom calc import add\n\n\n{body}")
    assert failed(checks) == {"V5"}, checks
    assert message in checks["V5"]["message"] and "test_x.py" in checks["V5"]["message"]


def test_v5_accepts_raises_and_an_expected_value_held_in_a_name(worktree):
    raises = "# CASE_ID: TC-APP-002\nimport pytest\nfrom calc import add\n\n\ndef test_a():\n    with pytest.raises(TypeError):\n        add(1, None)\n"
    assert not failed(run_checks(worktree, raises, "TC-APP-002"))
    named = "# CASE_ID: TC-APP-001\nfrom calc import add\n\n\ndef test_a():\n    want = 5\n    assert add(2, 3) == want\n"
    assert not failed(run_checks(worktree, named))


def test_v4_refuses_a_symbol_the_repository_does_not_define(worktree):
    checks = run_checks(worktree, "# CASE_ID: TC-APP-001\nfrom calc import subtract\n\n\ndef test_a():\n    assert subtract(8, 3) == 5\n")
    assert "V4" in failed(checks) and "subtract" in checks["V4"]["message"]


def test_v4_refuses_a_repository_module_that_does_not_exist(worktree):
    checks = run_checks(worktree, "# CASE_ID: TC-APP-001\nfrom app.missing import add\n\n\ndef test_a():\n    assert add(2, 3) == 5\n")
    assert "V4" in failed(checks) and "app.missing" in checks["V4"]["message"]


def test_an_import_of_a_module_nobody_has_fails_the_collect(worktree):
    checks = run_checks(worktree, "# CASE_ID: TC-APP-001\nfrom nowhere_at_all import add\n\n\ndef test_a():\n    assert add(2, 3) == 5\n")
    assert "V3" in failed(checks) and "nowhere_at_all" in checks["V3"]["message"]


def test_v3_refuses_a_syntax_error(worktree):
    checks = run_checks(worktree, "# CASE_ID: TC-APP-001\ndef test_a(:\n    assert 1 == 2\n")
    assert failed(checks) == {"V3"} and "test_x.py:2" in checks["V3"]["message"], checks


def test_v6_refuses_a_missing_case_id(worktree):
    checks = run_checks(worktree, GOOD.replace("# CASE_ID: TC-APP-001\n", ""))
    assert failed(checks) == {"V6"} and "carries no case id" in checks["V6"]["message"]


def test_v6_refuses_a_case_id_that_is_not_a_case(worktree):
    checks = run_checks(worktree, GOOD.replace("TC-APP-001", "TC-APP-099"))
    assert failed(checks) == {"V6"} and "TC-APP-099 is not a case" in checks["V6"]["message"]


def test_without_a_run_environment_v3_is_not_checked_and_the_test_is_not_valid(tmp_path):
    root = tmp_path / "wt"
    (root / "tests/agentic_qe").mkdir(parents=True)
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    checks = validity.check_file(root, "tests/agentic_qe/test_x.py", GOOD, ["TC-APP-001"], CASES)
    assert checks["V3"]["status"] == "NOT CHECKED" and "Install dependencies" in checks["V3"]["message"]
    done = validity.tally([{"path": "tests/agentic_qe/test_x.py", "case_id": "TC-APP-001", "checks": checks}])
    assert done["counts"]["valid"] == 0 and done["invalid"] == ["tests/agentic_qe/test_x.py"] and done["counts"]["V3"] == 1
    assert validity.line(done) == "Validity: 0 of 1 tests valid; 1 need review (V2b 0, V3 1, V4 0, V5 0, V6 0)."


def test_a_syntax_error_fails_v3_even_without_an_environment(tmp_path):
    checks = validity.check_file(tmp_path, "tests/agentic_qe/test_x.py", "def (:\n", ["TC-APP-001"], CASES)
    assert checks["V3"]["status"] == "FAIL"
