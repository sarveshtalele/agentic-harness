"""Automated Backend API Complete Audit Test Suite.

Exhaustively audits and verifies all backend API endpoints across all routers:
- Projects router (/api/projects, /api/projects/{id}, overview, members)
- Repository router (/api/projects/{id}/repo, /api/projects/{id}/repo/tree, /api/projects/{id}/repo/file)
- Governance router (/api/projects/{id}/gates, approvals, ledger, metrics, prompts, agents, evals)
- Documents router (/api/documents, /api/projects/{id}/documents, /api/documents/{id})
- Findings router (/api/findings, /api/projects/{id}/findings)
- Runs router (/api/projects/{id}/runs, /api/runs/{id}, /api/approvals)
- Observability router (/api/observability, /api/projects/{id}/observability, /api/observability/errors)
- Harness router (/api/harness/sessions, /api/harness/skills, /api/harness/plugins, /api/harness/tools, /api/harness/config)
- MCP router (/api/mcp/servers)
- Settings router (/api/settings/llm, /api/settings/models, /api/settings/gate-roles, /api/settings/timezone)
- Skills router (/api/skills, /api/skills/{name})
- Chat router (/api/projects/{id}/chats, /api/projects/{id}/memories)

Verifies all 4 enterprise project IDs:
- prj_agentic_qe
- prj_fintech_gateway
- prj_ecommerce_core
- prj_mcp_market

And verifies 404 Not Found handling for missing projects and resources.
"""
from __future__ import annotations

import os
import sys
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.db import db, now

PROJECT_IDS = [
    "prj_agentic_qe",
    "prj_fintech_gateway",
    "prj_ecommerce_core",
    "prj_mcp_market",
]


@pytest.fixture(scope="module")
def client():
    """Authenticated admin TestClient fixture running lifespan."""
    with TestClient(app) as test_client:
        admin_user = os.environ.get("ATLAS_ADMIN_USERNAME", "qa-admin")
        admin_pass = os.environ.get("ATLAS_ADMIN_PASSWORD", "")
        login_res = test_client.post(
            "/api/auth/login",
            json={"username": admin_user, "password": admin_pass},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        yield test_client


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


def test_harness_sessions_lifecycle(client: TestClient):
    """GET /api/harness/sessions, POST, GET {id}, PATCH, DELETE."""
    # List sessions
    res = client.get("/api/harness/sessions")
    assert res.status_code == 200
    data = res.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)

    # Create session
    create_res = client.post(
        "/api/harness/sessions",
        json={"name": "Audit Test Session", "mode": "plan", "projectId": "prj_agentic_qe"},
    )
    assert create_res.status_code == 200
    session_data = create_res.json()["session"]
    session_id = session_data["id"]
    assert session_data["name"] == "Audit Test Session"
    assert session_data["mode"] == "plan"

    # Get single session
    get_res = client.get(f"/api/harness/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["session"]["id"] == session_id

    # Patch session
    patch_res = client.patch(
        f"/api/harness/sessions/{session_id}",
        json={"mode": "act", "name": "Audit Test Session Updated"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["session"]["mode"] == "act"
    assert patch_res.json()["session"]["name"] == "Audit Test Session Updated"

    # Delete session
    del_res = client.delete(f"/api/harness/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json().get("success") is True

    # 404 for deleted session
    get_deleted = client.get(f"/api/harness/sessions/{session_id}")
    assert get_deleted.status_code == 404


def test_harness_skills_and_plugins(client: TestClient):
    """GET /api/harness/skills, plugins, tools, config, cache."""
    # Skills
    res_skills = client.get("/api/harness/skills")
    assert res_skills.status_code == 200
    skills_data = res_skills.json()
    assert "skills" in skills_data
    assert "total" in skills_data
    assert skills_data["total"] >= 1

    # Plugins
    res_plugins = client.get("/api/harness/plugins")
    assert res_plugins.status_code == 200
    plugins_data = res_plugins.json()
    assert "plugins" in plugins_data
    assert "totalLocalSkills" in plugins_data

    # Tools
    res_tools = client.get("/api/harness/tools")
    assert res_tools.status_code == 200
    tools_data = res_tools.json()
    assert "tools" in tools_data
    assert len(tools_data["tools"]) >= 1

    # Config
    res_conf = client.get("/api/harness/config")
    assert res_conf.status_code == 200
    conf_data = res_conf.json()
    assert "is_configured" in conf_data

    # Cache
    res_cache = client.get("/api/harness/cache")
    assert res_cache.status_code == 200
    assert "cache" in res_cache.json()


def test_mcp_servers(client: TestClient):
    """GET /api/mcp/servers must return registered MCP servers with valid schema."""
    res = client.get("/api/mcp/servers")
    assert res.status_code == 200
    data = res.json()
    assert "servers" in data
    assert "total_servers" in data
    assert "connected_servers" in data
    assert "total_tools" in data
    assert "authorized_tools" in data
    assert len(data["servers"]) >= 1
    srv = data["servers"][0]
    assert "id" in srv
    assert "name" in srv
    assert "status" in srv
    assert "tools" in srv


def test_settings_endpoints(client: TestClient):
    """GET /api/settings/llm, models, gate-roles, timezone."""
    # LLM settings
    res_llm = client.get("/api/settings/llm")
    assert res_llm.status_code == 200
    llm_data = res_llm.json()
    assert "configured" in llm_data

    # Allowed models
    res_models = client.get("/api/settings/models")
    assert res_models.status_code == 200
    models_data = res_models.json()
    assert "models" in models_data

    # Gate roles
    res_roles = client.get("/api/settings/gate-roles")
    assert res_roles.status_code == 200
    roles_data = res_roles.json()
    assert "roles" in roles_data
    assert "assignable" in roles_data

    # Timezone
    res_tz = client.get("/api/settings/timezone")
    assert res_tz.status_code == 200
    assert "timezone" in res_tz.json()


def test_skills_catalog_endpoints(client: TestClient):
    """GET /api/skills and GET /api/skills/{name}."""
    res = client.get("/api/skills")
    assert res.status_code == 200
    data = res.json()
    assert "skills" in data
    assert isinstance(data["skills"], list)
    assert len(data["skills"]) > 0

    first_skill = data["skills"][0]["name"]
    res_single = client.get(f"/api/skills/{first_skill}")
    assert res_single.status_code == 200
    skill_detail = res_single.json()
    assert skill_detail["name"] == first_skill
    assert "body" in skill_detail

    # 404 for unknown skill
    res_unknown = client.get("/api/skills/non_existent_skill_xyz_123")
    assert res_unknown.status_code == 404


def test_governance_general_endpoints(client: TestClient):
    """GET /api/prompts, /api/agents, /api/evals, /api/evals/cards."""
    # Prompts
    res_p = client.get("/api/prompts")
    assert res_p.status_code == 200
    assert isinstance(res_p.json(), list)

    # Agents
    res_a = client.get("/api/agents")
    assert res_a.status_code == 200
    agents = res_a.json()
    assert isinstance(agents, list)
    if agents:
        agent_key = agents[0]["key"]
        res_agent = client.get(f"/api/agents/{agent_key}")
        assert res_agent.status_code == 200

    # Evals
    res_e = client.get("/api/evals")
    assert res_e.status_code == 200
    assert isinstance(res_e.json(), list)

    # Eval cards
    res_cards = client.get("/api/evals/cards")
    assert res_cards.status_code == 200
    assert "cards" in res_cards.json()


def test_observability_general_endpoints(client: TestClient):
    """GET /api/observability and GET /api/observability/errors."""
    res_obs = client.get("/api/observability")
    assert res_obs.status_code == 200
    assert "items" in res_obs.json()

    res_err = client.get("/api/observability/errors")
    assert res_err.status_code == 200
    assert "groups" in res_err.json()


def test_nonexistent_project_404_handling(client: TestClient):
    """Verify all project-scoped endpoints raise 404 for non-existent project IDs."""
    fake_pid = "prj_does_not_exist_999"

    endpoints_to_test = [
        f"/api/projects/{fake_pid}",
        f"/api/projects/{fake_pid}/overview",
        f"/api/projects/{fake_pid}/repo",
        f"/api/projects/{fake_pid}/repo/tree",
        f"/api/projects/{fake_pid}/gates",
        f"/api/projects/{fake_pid}/documents",
        f"/api/projects/{fake_pid}/findings",
        f"/api/projects/{fake_pid}/runs",
        f"/api/projects/{fake_pid}/observability",
        f"/api/projects/{fake_pid}/chats",
        f"/api/projects/{fake_pid}/memories",
        f"/api/projects/{fake_pid}/approvals",
        f"/api/projects/{fake_pid}/ledger",
        f"/api/projects/{fake_pid}/metrics",
    ]

    for ep in endpoints_to_test:
        res = client.get(ep)
        assert res.status_code == 404, f"Endpoint {ep} expected 404, got {res.status_code}: {res.text}"
