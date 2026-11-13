"""R2 governance of features (docs/PHASE2_PLAN.md 12.3): role defaults, member overrides, the effective preview, the
ledger with before and after, and that only the admin changes any of it."""
from backend.core import ledger
from backend.core.auth import features
from tests.helpers_api import client, make_user, sign_in, unique  # noqa: F401 - fixtures


def test_role_defaults_decide_and_a_member_override_wins(client):
    name = unique("ba")
    member = make_user(client, name, role="ba")
    other, _ = sign_in(name)
    assert other.get("/api/features/me").json()["features"] == ["ba", "docs"]
    refused = other.get("/api/skill-studio/documents")
    assert refused.status_code == 403 and "Skill Studio" in refused.json()["message"]
    assert client.put(f"/api/features/overrides/{member['id']}", json={"feature": "skills", "allowed": True}).status_code == 200
    assert client.put(f"/api/features/overrides/{member['id']}", json={"feature": "docs", "allowed": False}).status_code == 200
    assert other.get("/api/skill-studio/documents").status_code != 403  # past the feature gate (422 asks for a project)
    assert other.get("/api/features/me").json()["features"] == ["ba", "skills"]
    assert client.get(f"/api/features/effective/{member['id']}").json()["features"] == ["ba", "skills"]  # the admin's preview
    assert client.put(f"/api/features/overrides/{member['id']}", json={"feature": "skills", "allowed": None}).status_code == 200
    assert other.get("/api/skill-studio/documents").status_code == 403  # removing the override goes back to the role default


def test_changes_are_ledgered_with_before_and_after_and_only_the_admin_changes(client):
    name = unique("dev")
    member = make_user(client, name, role="developer")
    other, _ = sign_in(name)
    before = client.get("/api/features").json()["roles"]["viewer"]
    assert client.put("/api/features/roles", json={"viewer": ["docs", "traces"]}).status_code == 200
    entry = ledger.entries(features.PLATFORM_PROJECT, 1)[0]
    assert entry["action"] == "features.roles_changed" and '"traces"' in entry["data"] and entry["actor"] == "admin"
    assert ledger.verify(features.PLATFORM_PROJECT)["valid"]
    client.put("/api/features/roles", json={"viewer": before})
    for call in (other.get("/api/features"), other.put("/api/features/roles", json={"developer": ["mcp"]}),
                 other.put(f"/api/features/overrides/{member['id']}", json={"feature": "mcp", "allowed": True})):
        assert call.status_code == 403
    assert client.put("/api/features/roles", json={"developer": ["teleport"]}).status_code == 400
    assert client.put("/api/features/roles", json={"admin": ["docs"]}).status_code == 400
    assert all(p["id"] != features.PLATFORM_PROJECT for p in client.get("/api/projects", params={"archived": True}).json())
