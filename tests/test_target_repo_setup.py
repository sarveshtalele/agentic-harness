"""Live: target project, repository and sandbox creation."""

from __future__ import annotations

import pytest

from backend.config import repo_dir, sandbox_dir
from backend.db import db, row
from backend.repos import sandbox
from backend.core.security import safe_path
from backend.core.errors import RepoError
from tests.helpers_target_repo import setup_target_project_and_sandbox, TARGET_NAME, TARGET_PROJECT_ID  # noqa: F401 - fixtures

pytestmark = pytest.mark.live


def test_database_project_exists():
    """Verify prj_mcp_market is registered in the platform database with correct name."""
    with db() as con:
        p = row(con.execute("SELECT id, name, description, owner_id FROM projects WHERE id=?", (TARGET_PROJECT_ID,)))
    
    assert p is not None, f"Project '{TARGET_PROJECT_ID}' must exist in database"
    assert p["name"] == TARGET_NAME
    assert p["owner_id"] is not None


def test_repo_and_sandbox_creation_and_structure():
    """Verify directory structure and git repos for both base repo and sandbox."""
    r_dir = repo_dir(TARGET_PROJECT_ID)
    s_dir = sandbox_dir(TARGET_PROJECT_ID)

    assert r_dir.exists(), f"Repo directory {r_dir} must exist"
    assert (r_dir / ".git").exists(), "Repo must contain .git"
    assert (r_dir / "backend").exists(), "Repo must contain backend folder"
    assert (r_dir / "frontend").exists(), "Repo must contain frontend folder"

    # Verify sandbox is active
    assert s_dir.exists(), "Sandbox directory must exist"
    assert (s_dir / ".git").exists(), "Sandbox must contain .git repository"
    assert (s_dir / "backend" / "app").exists(), "Sandbox must contain backend/app"
    assert (s_dir / "frontend" / "package.json").exists(), "Sandbox must contain frontend/package.json"

    # Verify sandbox metadata
    info = sandbox.info(TARGET_PROJECT_ID)
    assert info["sandbox_ready"] is True
    assert info["sandbox_initialized"] is True
    assert info["commit"] != ""
    assert int(info["commits"]) >= 1


def test_sandbox_file_creation_and_traversal_blocking():
    """Verify safe file creation in sandbox and strict containment against path traversal."""
    s_dir = sandbox_dir(TARGET_PROJECT_ID)

    # 1. Create a safe verification file
    rel_path = "docs/qe_sandbox_marker.json"
    content = '{"pipeline": "qe-validation", "verified": true}'
    res = sandbox.create_file(TARGET_PROJECT_ID, rel_path, content, target="sandbox")
    
    assert res["status"] == "created"
    target_file = s_dir / rel_path
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == content

    # 2. Verify path traversal rejection
    traversal_targets = [
        "../../outside_marker.txt",
        "/etc/passwd",
        "../../../etc/shadow",
        "sub/../../../../target.sh"
    ]
    for bad_path in traversal_targets:
        with pytest.raises((ValueError, RepoError)):
            safe_path(s_dir, bad_path, for_write=True)
