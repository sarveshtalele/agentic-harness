"""The QE runner is decided by code, not by the model's free-text framework label (live run: "python" ran nothing)."""
from backend.qe.execution import pick_runner


def test_label_naming_a_runner_is_used():
    assert pick_runner("pytest 8", ["tests/agentic_qe/test_a.py"]) == ("pytest", "")
    assert pick_runner("Playwright TS", ["e2e/a.spec.ts"]) == ("playwright", "")


def test_unknown_label_with_python_files_runs_pytest_and_says_so():
    runner, note = pick_runner("python", ["tests/agentic_qe/test_a.py", "tests/agentic_qe/test_b.py"])
    assert runner == "pytest" and "python" in note


def test_unknown_label_with_js_files_stays_unresolved():
    runner, note = pick_runner("typescript", ["tests/a.test.ts"])
    assert runner == "typescript" and note  # build_command returns None, so the verdict is INCONCLUSIVE with a reason
