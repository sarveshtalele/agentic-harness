"""Phase R registry reads per user: a member sees only granted plugins and granted MCP tools; an admin sees all; only an admin syncs."""
from backend.core import plugin_grants
from backend.core.mcp import grants, registry as mcp
from tests.helpers_api import client, make_user, sign_in, unique  # noqa: F401 - fixtures


def _member(admin, role="developer"):
    name = unique(role)
    make_user(admin, name, role=role)
    other, signed = sign_in(name)
    assert signed.status_code == 200
    return other


def _names(c, **params):
    found = c.get("/api/capabilities", params=params)
    assert found.status_code == 200, found.text
    return {i["qualified_name"] for i in found.json()["items"]}


def test_member_sees_only_granted_plugin_skills_and_mcp_tools(client):
    member = _member(client)
    server = mcp.add({"name": unique("srv"), "transport": "http", "url": "https://mcp.example.test/mcp"}, owner="admin")
    mcp.store_tools(server["id"], [{"name": "granted_tool", "description": "Granted", "input_schema": {}},
                                   {"name": "secret_tool", "description": "Not granted", "input_schema": {}}])
    grant = grants.add(server["id"], "granted_tool", "developer", "admin")
    plugin_grant = plugin_grants.add("agentic-qe", "ba", "admin")
    try:
        assert client.post("/api/capabilities/sync").status_code == 200
        assert "agentic-qe:planning-tests" not in _names(member, kind="skill")
        assert "agentic-qe:planning-tests" in _names(client, kind="skill")
        assert "local-skills:planning-tests" in _names(member, kind="skill"), "an ungranted plugin hides only its own skills"
        tools = f"{server['name']}:"
        assert {n for n in _names(member, kind="mcp_tool") if n.startswith(tools)} == {tools + "granted_tool"}
        assert {n for n in _names(client, kind="mcp_tool") if n.startswith(tools)} == {tools + "granted_tool", tools + "secret_tool"}
        hidden = client.get("/api/capabilities/agentic-qe:qe-plan").json()["id"]
        assert member.get(f"/api/capabilities/{hidden}").status_code == 404
        assert client.get(f"/api/capabilities/{hidden}").json()["qualified_name"] == "agentic-qe:qe-plan"
        tree = member.get("/api/capabilities/tree").json()["roots"]
        assert "agentic-qe" not in {r["qualified_name"] for r in tree}
    finally:
        plugin_grants.remove("agentic-qe", plugin_grant["id"], "admin")
        grants.remove(grant["id"])
        mcp.delete(server["id"])
        client.post("/api/capabilities/sync")


def test_only_an_admin_can_sync(client):
    member = _member(client, "qe_lead")
    assert member.post("/api/capabilities/sync").status_code == 403
    assert member.get("/api/capabilities").status_code == 200
    done = client.post("/api/capabilities/sync")
    assert done.status_code == 200 and len(done.json()["hash"]) == 64


def test_detail_has_links_up_and_down(client):
    client.post("/api/capabilities/sync")
    found = client.get("/api/capabilities/agentic-qe:qe-plan").json()
    assert ("applies_skill", "agentic-qe:planning-tests") in {(l["relation"], l["qualified_name"]) for l in found["down"]}
    assert ("contains", "agentic-qe") in {(l["relation"], l["qualified_name"]) for l in found["up"]}
    qe = next(r for r in client.get("/api/capabilities/tree").json()["roots"] if r["kind"] == "workflow" and r["name"] == "qe")
    plan = next(s for s in qe["children"] if s["name"] == "plan")
    assert [a["name"] for a in plan["children"] if a["kind"] == "agent"] == ["principal-test-architect"]
