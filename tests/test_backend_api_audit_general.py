"""Backend API audit: MCP, settings, skills, governance, observability, and 404 handling."""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from tests.helpers_audit import PROJECT_IDS, client  # noqa: F401 - fixtures


def test_mcp_servers(client: TestClient):
    """Nothing is seeded: a server appears only once an admin registers it, and its tools only after a real connect."""
    from backend.config import ROOT
    data = client.get("/api/mcp/servers").json()
    for key in ("servers", "total_servers", "connected_servers", "total_tools", "authorized_tools"):
        assert key in data
    assert not {s["id"] for s in data["servers"]} & {"mcp-filesystem", "mcp-memory", "mcp-fetch", "mcp-github", "srv_playwright"}
    assert {"playwright", "filesystem", "fetch", "github"} <= {t["id"] for t in client.get("/api/mcp/catalog").json()["templates"]}
    made = client.post("/api/mcp/servers", json={"name": "audit echo", "command": sys.executable, "args": [str(ROOT / "tests" / "fixtures" / "mcp_echo_server.py")]})
    assert made.status_code == 201 and made.json()["status"] == "not_connected" and made.json()["tools"] == []
    srv = client.post(f"/api/mcp/servers/{made.json()['id']}/connect").json()
    assert srv["status"] == "connected" and {t["name"] for t in srv["tools"]} == {"echo", "add"}
    listed = next(s for s in client.get("/api/mcp/servers").json()["servers"] if s["id"] == srv["id"])
    assert {"id", "name", "status", "tools"} <= set(listed)
    assert client.delete(f"/api/mcp/servers/{srv['id']}").status_code == 200


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
