"""HS-12 plugin grants per role: no grant means open; a grant limits skills and the "/" menu to that role
and the admin; only an admin grants; every change is in the ledger."""
from agent_framework import SkillsSourceContext

from backend.core import auth, ledger, plugin_grants, plugins
from backend.core.skills import _run
from tests.helpers_api import client, make_user, project, sign_in, unique  # noqa: F401 - fixtures
from tests.test_plugins_state import _plugin


def _clear(plugin_id: str) -> None:
    for grant in plugin_grants.listing(plugin_id):
        plugin_grants.remove(plugin_id, grant["id"], "admin")


def _account(admin, role: str):
    name = unique(role)
    make_user(admin, name, role=role)
    other, signed = sign_in(name)
    assert signed.status_code == 200
    return other


def test_no_grants_is_open_and_a_ba_grant_limits_skills_and_menu(tmp_path):
    pid = unique("plug")
    folder = (_plugin(tmp_path, pid) / "skills").resolve()
    assert plugin_grants.listing(pid) == []
    for role in (None, "admin", "ba", "developer", "qe_lead"):
        assert folder in plugins.skill_paths(tmp_path, role=role)
    plugin_grants.add(pid, "ba", "admin")
    assert folder not in plugins.skill_paths(tmp_path, role="developer")
    assert folder in plugins.skill_paths(tmp_path, role="ba") and folder in plugins.skill_paths(tmp_path, role="admin")
    assert folder in plugins.skill_paths(tmp_path)  # a caller without a user is not filtered
    menu = lambda role: [e for e in plugins.slash_entries(tmp_path, role=role) if e["plugin"] == pid]
    assert menu("developer") == [] and menu("ba") and menu("admin")
    assert plugins.skill_paths(tmp_path, role="developer")[0] == plugins.SKILLS_DIR  # other plugins stay


def test_api_grants_are_admin_only_filter_the_menu_and_are_ledgered(client, project):
    _clear("agentic-qe")
    developer, ba = _account(client, "developer"), _account(client, "ba")
    ours = lambda c: [e for e in c.get("/api/plugins/slash").json() if e["plugin"] == "agentic-qe"]
    assert ours(developer) and ours(ba), "no grants: open to every role"
    assert developer.post("/api/plugins/agentic-qe/grants", json={"role": "developer"}).status_code == 403
    assert client.post("/api/plugins/agentic-qe/grants", json={"role": "nobody"}).status_code == 400
    assert client.post("/api/plugins/no-such-plugin/grants", json={"role": "ba"}).status_code == 404
    made = client.post("/api/plugins/agentic-qe/grants", json={"role": "ba"})
    assert made.status_code == 201 and made.json()["role"] == "ba" and made.json()["granted_by"] == auth.ADMIN_ID
    try:
        assert ours(developer) == [] and ours(ba) and ours(client)
        listed = developer.get("/api/plugins/agentic-qe/grants").json()  # read-only for everyone signed in
        assert [g["role"] for g in listed["grants"]] == ["ba"] and listed["roles"] == list(auth.ROLES)
        added = [e for e in ledger.entries(project["id"]) if e["action"] == "plugin.grant_added" and made.json()["id"] in e["data"]]
        assert added and added[0]["target"] == "agentic-qe" and added[0]["actor"] == auth.ADMIN_ID
        assert developer.delete(f"/api/plugins/agentic-qe/grants/{made.json()['id']}").status_code == 403
    finally:
        assert client.delete(f"/api/plugins/agentic-qe/grants/{made.json()['id']}").status_code == 200
    assert [e for e in ledger.entries(project["id"]) if e["action"] == "plugin.grant_removed" and made.json()["id"] in e["data"]]
    assert ours(developer), "the last grant removed: open again"
    assert auth.rule_of("/api/plugins/agentic-qe/grants") == "session" and auth.rule_of("/api/plugins/agentic-qe/grants/pgr_1") == "session"
