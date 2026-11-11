"""Live: sandbox commands, the health endpoint and git."""

from __future__ import annotations

import pytest

from backend.config import sandbox_dir

from backend.repos import sandbox, git
from tests.helpers_target_repo import setup_target_project_and_sandbox, TARGET_PROJECT_ID, VALIDATION_BRANCH  # noqa: F401 - fixtures

pytestmark = pytest.mark.live


def test_npx_execution_in_sandbox():
    """Verify running npx commands cleanly inside the sandbox environment."""
    # 1. Basic npx version check
    res_version = sandbox.run_npx(TARGET_PROJECT_ID, "--version")
    assert res_version["status"] == "success"
    assert res_version["exit_code"] == 0
    assert len(res_version["stdout"].strip()) > 0

    # 2. npx typescript check in frontend directory
    frontend_dir = sandbox_dir(TARGET_PROJECT_ID) / "frontend"
    res_tsc = sandbox.run_npx(TARGET_PROJECT_ID, "tsc --version", cwd=frontend_dir)
    assert res_tsc["status"] == "success"
    assert res_tsc["exit_code"] == 0
    assert "Version" in res_tsc["stdout"]


def test_feature_building_and_health_diagnostic_endpoint():
    """Verify the feature implementation (/health/diagnostic) is present in backend/app/main.py."""
    s_dir = sandbox_dir(TARGET_PROJECT_ID)
    main_py = s_dir / "backend" / "app" / "main.py"
    assert main_py.exists(), "backend/app/main.py must exist"

    code = main_py.read_text(encoding="utf-8")
    assert "/health/diagnostic" in code
    assert "health_diagnostic" in code
    assert "schema_version" in code


def test_test_execution_without_timeout():
    """Verify test runners execute without arbitrary short timeouts (timeout=None and timeout=600)."""
    backend_dir = sandbox_dir(TARGET_PROJECT_ID) / "backend"
    
    # 1. Run schema validation test with timeout=None
    cmd_val = "python3 -m pytest tests/test_health_and_schema_validation.py"
    res_val = sandbox.run_tests(
        TARGET_PROJECT_ID,
        cmd_val,
        cwd=backend_dir,
        timeout=None
    )
    assert res_val["status"] == "success", f"Failed with: {res_val.get('stderr') or res_val.get('stdout')}"
    assert res_val["exit_code"] == 0
    assert "passed" in res_val["stdout"]

    # 2. Run calculations test with timeout=600
    cmd_calc = "python3 -m pytest tests/test_calculations.py"
    res_calc = sandbox.run_tests(
        TARGET_PROJECT_ID,
        cmd_calc,
        cwd=backend_dir,
        timeout=600
    )
    assert res_calc["status"] == "success", f"Failed with: {res_calc.get('stderr') or res_calc.get('stdout')}"
    assert res_calc["exit_code"] == 0
    assert "passed" in res_calc["stdout"]


def test_git_branch_and_commits():
    """Verify git branch test/harness-qe-validation and its commits. (The PR simulation was fabricated and is retired.)"""
    s_dir = sandbox_dir(TARGET_PROJECT_ID)

    # 1. Verify current branch is test/harness-qe-validation
    current_branch = git.run(["branch", "--show-current"], cwd=s_dir)
    assert current_branch == VALIDATION_BRANCH

    # 2. Verify commits on the validation branch beyond origin/main
    commits = git.run(["log", f"origin/main..{VALIDATION_BRANCH}", "--oneline"], cwd=s_dir)
    assert len(commits.strip()) > 0
    assert "feat(qe)" in commits or "docs(qe)" in commits
