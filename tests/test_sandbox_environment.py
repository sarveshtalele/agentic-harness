"""Unit and integration tests for the Project Sandbox Environment.
Tests workspace creation, safe file writes, path traversal defenses,
code execution containment, and dependency management.
"""
import os
import sys
import pytest

from backend.repos import sandbox
from backend.core.security import safe_path
from backend.core.errors import RepoError


def test_ensure_sandbox_creates_repo_and_git():
    """Verify ensure_sandbox creates repo directory with valid git repository and initial commit."""
    test_project = "prj_unit_sandbox_test"
    repo_path = sandbox.ensure_sandbox(test_project)
    
    assert repo_path.exists()
    assert (repo_path / ".git").exists()
    assert (repo_path / "README.md").exists()
    
    # Verify sandbox info
    info = sandbox.info(test_project)
    assert info["sandbox_ready"] is True
    assert info["commit"] != ""
    assert int(info["commits"]) >= 1


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
