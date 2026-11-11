"""Backend API audit: documents, findings, runs, observability, and overview endpoints per project."""
from __future__ import annotations


from fastapi.testclient import TestClient

from tests.helpers_audit import PROJECT_IDS, client  # noqa: F401 - fixtures


def test_get_project_documents_all_projects(client: TestClient):
    """GET /api/projects/{id}/documents must return a list of documents for each project."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/documents")
        assert res.status_code == 200, f"GET /api/projects/{pid}/documents failed: {res.text}"
        docs = res.json()
        assert isinstance(docs, list)
        for d in docs:
            assert "id" in d
            assert "project_id" in d
            assert d["project_id"] == pid
            assert "kind" in d
            assert "title" in d
            assert "status" in d


def test_get_project_findings_all_projects(client: TestClient):
    """GET /api/projects/{id}/findings must return findings array for each project."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/findings")
        assert res.status_code == 200, f"GET /api/projects/{pid}/findings failed: {res.text}"
        findings = res.json()
        assert isinstance(findings, list)
        for f in findings:
            assert "id" in f
            assert "project_id" in f
            assert f["project_id"] == pid
            assert "severity" in f
            assert "status" in f


def test_get_project_runs_all_projects(client: TestClient):
    """GET /api/projects/{id}/runs must return runs array for each project."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/runs")
        assert res.status_code == 200, f"GET /api/projects/{pid}/runs failed: {res.text}"
        runs = res.json()
        assert isinstance(runs, list)
        for r in runs:
            assert "id" in r
            assert "workflow" in r
            assert "status" in r


def test_get_project_observability_all_projects(client: TestClient):
    """GET /api/projects/{id}/observability must return observability report for each project."""
    for pid in PROJECT_IDS:
        res = client.get(f"/api/projects/{pid}/observability")
        assert res.status_code == 200, f"GET /api/projects/{pid}/observability failed: {res.text}"
        obs = res.json()
        assert "items" in obs
        assert isinstance(obs["items"], list)
        assert "total" in obs
        assert "counts" in obs
        assert "errors" in obs
        assert "tokens" in obs
        assert "runs" in obs
        assert "integrity" in obs


def test_project_overview_and_metadata_endpoints(client: TestClient):
    """GET /api/projects/{id}/overview, approvals, ledger, metrics, chats, memories."""
    for pid in PROJECT_IDS:
        # Overview
        res_ov = client.get(f"/api/projects/{pid}/overview")
        assert res_ov.status_code == 200
        ov = res_ov.json()
        assert "project" in ov
        assert "gates" in ov
        assert "pending_approvals" in ov
        assert "recent_runs" in ov
        assert "documents" in ov

        # Approvals
        res_appr = client.get(f"/api/projects/{pid}/approvals")
        assert res_appr.status_code == 200
        assert isinstance(res_appr.json(), list)

        # Ledger
        res_ledg = client.get(f"/api/projects/{pid}/ledger")
        assert res_ledg.status_code == 200
        ledg = res_ledg.json()
        assert "entries" in ledg
        assert "verification" in ledg

        # Metrics
        res_met = client.get(f"/api/projects/{pid}/metrics")
        assert res_met.status_code == 200
        met = res_met.json()
        assert "runs" in met
        assert "durations" in met
        assert "tools" in met
        assert "agents" in met

        # Chats
        res_chat = client.get(f"/api/projects/{pid}/chats")
        assert res_chat.status_code == 200
        assert isinstance(res_chat.json(), list)

        # Memories
        res_mem = client.get(f"/api/projects/{pid}/memories")
        assert res_mem.status_code == 200
        assert isinstance(res_mem.json(), list)
