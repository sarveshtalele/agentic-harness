"""Tests for repository backend endpoints, data ingestion, and analysis normalization."""
import os
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.repos import ingest


@pytest.fixture
def client():
    with TestClient(app) as c:
        admin_user = os.environ.get("ATLAS_ADMIN_USERNAME", "qa-admin")
        admin_pass = os.environ.get("ATLAS_ADMIN_PASSWORD", "admin")
        login = c.post("/api/auth/login", json={"username": admin_user, "password": admin_pass})
        assert login.status_code == 200
        yield c


def test_analysis_normalization_with_empty_dict():
    norm = ingest.normalize_analysis({})
    assert norm["mode"] == "brownfield"
    assert norm["total_files"] == 0
    assert norm["source_files"] == 0
    assert norm["test_file_count"] == 0
    assert norm["test_files"] == []
    assert norm["languages"] == {}
    assert norm["lines_of_code"] == {}
    assert norm["frameworks"] == []
    assert norm["test_runners"] == []
    assert norm["routes"] == []
    assert norm["ci"] == []
    assert norm["entrypoints"] == []
    assert norm["manifests"] == {"dependencies": {}, "scripts": {}}
    assert norm["docs"] == []
    assert norm["top_imports"] == []


def test_analysis_normalization_never_estimates_lines_of_code(tmp_path):
    # a list of language names says nothing about size, so no line count is made up
    norm = ingest.normalize_analysis({"languages": ["TypeScript", "Python"], "frameworks": ["FastAPI", "React"]})
    assert norm["lines_of_code"] == {} and norm["source_files"] == 0 and norm["frameworks"] == ["FastAPI", "React"]
    (tmp_path / "app.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x\n", encoding="utf-8")
    counted = ingest.normalize_analysis({}, tmp_path)
    assert counted["lines_of_code"] == {"Python": 3} and counted["total_files"] == 2 and counted["source_files"] == 1


def test_analysis_normalization_top_imports_as_list():
    raw = {"top_imports": {"fastapi": 10, "pytest": 5}}
    norm = ingest.normalize_analysis(raw)
    assert isinstance(norm["top_imports"], list)
    assert "fastapi" in norm["top_imports"]
    assert "pytest" in norm["top_imports"]


def test_uploaded_repository_has_measured_analysis_tree_and_files(client):
    import io
    import zipfile
    project_id = client.post("/api/projects", json={"name": "Repo shop", "description": "repo"}).json()["id"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("README.md", "# Repo shop\n")
        bundle.writestr("app.py", "def add(a, b):\n    return a + b\n")
        bundle.writestr("tests/test_app.py", "from app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n")
    assert client.post(f"/api/projects/{project_id}/repo/zip", files={"file": ("code.zip", buffer.getvalue(), "application/zip")}).status_code in (200, 201)

    # 1. /api/projects/{id}/repo
    res = client.get(f"/api/projects/{project_id}/repo")
    assert res.status_code == 200
    repo = res.json()
    assert repo is not None, f"Project {project_id} returned null repo"
    assert repo["kind"] in ("git", "github", "local", "zip")
    assert "analysis" in repo

    a = repo["analysis"]
    required_keys = [
        "mode", "total_files", "source_files", "test_file_count", "test_files",
        "languages", "lines_of_code", "frameworks", "test_runners", "routes",
        "ci", "entrypoints", "manifests", "docs", "top_imports"
    ]
    for k in required_keys:
        assert k in a, f"Missing key {k} in analysis of {project_id}"

    assert isinstance(a["mode"], str)
    assert isinstance(a["total_files"], int) and a["total_files"] > 0
    assert isinstance(a["source_files"], int) and a["source_files"] > 0
    assert isinstance(a["test_file_count"], int)
    assert isinstance(a["test_files"], list)
    assert isinstance(a["languages"], dict) and len(a["languages"]) > 0
    assert isinstance(a["lines_of_code"], dict) and len(a["lines_of_code"]) > 0
    assert isinstance(a["frameworks"], list)
    assert isinstance(a["test_runners"], list)
    assert isinstance(a["routes"], list)
    assert isinstance(a["ci"], list)
    assert isinstance(a["entrypoints"], list)
    assert isinstance(a["manifests"], dict)
    assert isinstance(a["docs"], list)
    assert isinstance(a["top_imports"], list)

    # 2. /api/projects/{id}/repo/tree
    tree_res = client.get(f"/api/projects/{project_id}/repo/tree")
    assert tree_res.status_code == 200
    tree = tree_res.json()
    assert "files" in tree
    assert len(tree["files"]) > 0

    # 3. Read first file from tree
    first_file = tree["files"][0]
    file_res = client.get(f"/api/projects/{project_id}/repo/file?path={first_file}")
    assert file_res.status_code == 200
    assert len(file_res.text) > 0


def test_repo_file_404_on_missing_file(client):
    res = client.get(f"/api/projects/{_project_with_repo(client)}/repo/file?path=does_not_exist.txt")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data
    assert "File not found" in data["detail"]


def test_repo_tree_empty_when_no_repo(client):
    # Create a project with no repo connected
    from backend.db import db, now
    with db() as con:
        con.execute(
            "INSERT OR REPLACE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) VALUES (?, ?, ?, ?, ?, 0, 'admin')",
            ("prj_empty", "Empty Project", "Test project with no repo", now(), now())
        )
    res = client.get("/api/projects/prj_empty/repo/tree")
    assert res.status_code == 200
    assert res.json() == {"files": []}


def _project_with_repo(client) -> str:
    from tests.conftest import connect_test_repo
    project_id = client.post("/api/projects", json={"name": "Repo 404", "description": ""}).json()["id"]
    connect_test_repo(project_id)
    return project_id
