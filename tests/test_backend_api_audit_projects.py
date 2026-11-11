"""Backend API audit: health and the per-project read endpoints."""
from __future__ import annotations


from fastapi.testclient import TestClient

from tests.helpers_audit import PROJECT_IDS, client  # noqa: F401 - fixtures


def test_health_and_auth_status(client: TestClient):
    """GET /api/health and GET /api/auth/status must return 200 and expected health structure."""
    res = client.get("/api/health")
    assert res.status_code == 200
    health = res.json()
    assert health["status"] == "ok"
    assert "skills" in health
    assert "tool_checks" in health

    res_auth = client.get("/api/auth/status")
    assert res_auth.status_code == 200
    assert res_auth.json().get("configured") is True


def test_list_projects(client: TestClient):
    """GET /api/projects must list projects including all 4 target enterprise projects."""
    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()
    assert isinstance(projects, list)
    pids = [p["id"] for p in projects]

    for expected_pid in PROJECT_IDS:
        assert expected_pid in pids, f"Expected project {expected_pid} in /api/projects"

    for p in projects:
        assert "id" in p
        assert "name" in p
        assert "description" in p
        assert "owner_id" in p
        assert "documents" in p
        assert "runs" in p
        assert "findings" in p
        assert "pending" in p
        assert "gates_approved" in p
        assert "can_write" in p
        assert "can_sign" in p


def test_get_project_detail_all_projects(client: TestClient):
    """GET /api/projects/{id} must return 200 and proper metadata for all 4 project IDs."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}")
        assert res.status_code == 200, f"GET /api/projects/{pid} failed: {res.text}"
        data = res.json()
        assert data["id"] == pid
        assert data["name"]
        assert isinstance(data["can_sign"], list)
        assert isinstance(data["documents"], int)
        assert isinstance(data["runs"], int)
        assert isinstance(data["findings"], int)


def test_get_project_repo_all_projects(client: TestClient):
    """GET /api/projects/{id}/repo must return repository status or null without crashing."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/repo")
        assert res.status_code == 200, f"GET /api/projects/{pid}/repo failed: {res.text}"
        data = res.json()
        if data is not None:
            assert "url" in data or "kind" in data
            assert "sandbox" in data
            assert "sandbox_ready" in data["sandbox"]


def test_get_project_repo_tree_all_projects(client: TestClient):
    """GET /api/projects/{id}/repo/tree must return files list for all 4 projects."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/repo/tree")
        assert res.status_code == 200, f"GET /api/projects/{pid}/repo/tree failed: {res.text}"
        data = res.json()
        assert "files" in data
        assert isinstance(data["files"], list)


def test_get_project_gates_all_projects(client: TestClient):
    """GET /api/projects/{id}/gates must return 6 sequential quality gates G0-G5 for all projects."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/gates")
        assert res.status_code == 200, f"GET /api/projects/{pid}/gates failed: {res.text}"
        gates = res.json()
        assert isinstance(gates, list)
        assert len(gates) >= 6
        gate_nums = [g["gate"] for g in gates]
        for g_idx in range(6):
            assert g_idx in gate_nums, f"Gate {g_idx} missing for project {pid}"

        for g in gates:
            assert "gate" in g
            assert "name" in g
            assert "description" in g
            assert "status" in g
            assert g["status"] in ("approved", "pending", "rejected", "draft")
