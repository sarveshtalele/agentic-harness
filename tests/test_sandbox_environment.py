"""Unit and integration tests for the Project Sandbox Environment.
Tests workspace creation, safe file writes, path traversal defenses,
code execution containment, and dependency management.
"""
import pytest

from backend.repos import sandbox
from backend.core.security import safe_path
from backend.core.errors import RepoError
from tests.conftest import connect_test_repo


@pytest.fixture(autouse=True)
def _connected():
    connect_test_repo("prj_unit_sandbox_test")


def test_ensure_sandbox_refuses_without_a_repository_and_invents_nothing():
    """Without a connected repository there is no sandbox, and no README or commit is made up in its place."""
    empty = "prj_unit_sandbox_empty"
    with pytest.raises(RepoError):
        sandbox.ensure_sandbox(empty)
    assert not (sandbox.repo_dir(empty) / "README.md").exists()
    assert sandbox.info(empty)["sandbox_ready"] is False
    info = sandbox.info("prj_unit_sandbox_test")
    assert info["sandbox_ready"] is True and info["commit"] != "" and int(info["commits"]) >= 1


def test_sandbox_create_file_safe():
    """Verify safe file creation inside sandbox."""
    test_project = "prj_unit_sandbox_test"
    res = sandbox.create_file(test_project, "src/calculator.py", "def add(a, b):\n    return a + b\n")
    
    assert res["status"] == "created"
    assert res["path"] == "src/calculator.py"
    assert res["size"] > 0
    
    # Verify file exists on disk
    repo_path = sandbox.ensure_sandbox(test_project)
    target = repo_path / "src" / "calculator.py"
    assert target.exists()
    assert "def add" in target.read_text()


def test_sandbox_path_traversal_blocked():
    """Verify path traversal attempts outside sandbox are strictly rejected."""
    test_project = "prj_unit_sandbox_test"
    repo_path = sandbox.ensure_sandbox(test_project)
    
    traversal_targets = [
        "../../outside.txt",
        "/etc/passwd",
        "../../../secret.env",
        "sub/../../../../target.sh"
    ]
    
    for bad_path in traversal_targets:
        with pytest.raises((ValueError, RepoError)):
            safe_path(repo_path, bad_path, for_write=True)


def test_sandbox_execute_python_code():
    """Verify Python code execution inside sandbox captures stdout/stderr with clean isolation."""
    test_project = "prj_unit_sandbox_test"
    calc_code = """
import decimal
a = decimal.Decimal('0.1')
b = decimal.Decimal('0.2')
print(f"CALC_RESULT:{a + b}")
"""
    result = sandbox.execute_code(test_project, calc_code, runtime="python")
    
    assert result["status"] == "success"
    assert result["exit_code"] == 0
    assert "CALC_RESULT:0.3" in result["stdout"]


def test_sandbox_execute_code_syntax_error_handling():
    """Verify code execution captures syntax/runtime errors gracefully without crashing backend."""
    test_project = "prj_unit_sandbox_test"
    bad_code = "print(10 / 0)"
    result = sandbox.execute_code(test_project, bad_code, runtime="python")
    
    assert result["status"] == "error"
    assert result["exit_code"] != 0
    assert "ZeroDivisionError" in result["stderr"]
