"""Roles: gate signing by role."""
from backend.db import db
from tests.helpers_access import IDS, World, account, world  # noqa: F401 - fixtures
from tests.helpers_api import USER_PASSWORD, client, make_user, sign_in, unique  # noqa: F401 - fixtures


# ---- gate roles ----

def test_gate_role_map_allows_and_refuses_by_role(world):
    pid = world.project["id"]
    sign = lambda who, gate: who.post(f"/api/projects/{pid}/gates/{gate}/decision", json={"approved": True})
    assert sign(world.dev, 0).status_code == 200, "with no map, any member who can write may sign"
    assert world.stranger.put("/api/settings/gate-roles", json={"roles": {"5": ["qe_lead"]}}).status_code == 403
    assert world.admin.put("/api/settings/gate-roles", json={"roles": {"9": ["qe_lead"]}}).status_code == 400
    assert world.admin.put("/api/settings/gate-roles", json={"roles": {"5": ["viewer"]}}).status_code == 400
    saved = world.admin.put("/api/settings/gate-roles", json={"roles": {"5": ["qe_lead"], "1": ["ba", "qe_lead"]}})
    assert saved.status_code == 200 and saved.json()["roles"] == {"1": ["ba", "qe_lead"], "5": ["qe_lead"]}
    try:
        refused = sign(world.dev, 5)
        assert refused.status_code == 403 and "QE lead" in refused.json()["message"], refused.text and "G5" in refused.json()["message"]
        assert sign(world.dev, 1).status_code == 403 and "BA" in sign(world.dev, 1).json()["message"]
        assert sign(world.lead, 5).status_code == 403, "a qe_lead account that is only a developer in this project holds the lesser role"
    finally:
        world.admin.put("/api/settings/gate-roles", json={"roles": {}})
    assert world.admin.get("/api/settings/gate-roles").json()["roles"] == {}


def test_a_qe_lead_who_holds_the_role_in_both_places_passes_the_role_check(world):
    pid = world.project["id"]
    world.add(world.lead_user, "qe_lead")  # now qe_lead on the account and in the project
    world.admin.put("/api/settings/gate-roles", json={"roles": {"5": ["qe_lead"]}})
    try:
        passed = world.lead.post(f"/api/projects/{pid}/gates/5/decision", json={"approved": True})
        assert passed.status_code == 400 and "Gate 4 must be approved" in passed.json()["message"]  # past the role check, stopped by order
        assert world.owner.post(f"/api/projects/{pid}/gates/5/decision", json={"approved": True}).status_code == 403  # a developer account owner
        assert world.admin.post(f"/api/projects/{pid}/gates/5/decision", json={"approved": True}).status_code == 400  # the admin is never role-blocked
    finally:
        world.admin.put("/api/settings/gate-roles", json={"roles": {}})


def test_gate_approval_from_a_run_is_checked_by_role_in_the_engine(world):
    pid = world.project["id"]
    with db() as con:
        con.execute("UPDATE approvals SET gate=5 WHERE id=?", (world.ids["approval_id"],))
    world.admin.put("/api/settings/gate-roles", json={"roles": {"5": ["qe_lead"]}})
    try:
        refused = world.dev.post(f"/api/approvals/{world.ids['approval_id']}/decide", json={"approved": True})
        assert refused.status_code == 403 and "QE lead" in refused.json()["message"], refused.text
        assert world.viewer.post(f"/api/approvals/{world.ids['approval_id']}/decide", json={"approved": True}).status_code == 403
    finally:
        world.admin.put("/api/settings/gate-roles", json={"roles": {}})
    with db() as con:
        assert con.execute("SELECT status FROM approvals WHERE id=?", (world.ids["approval_id"],)).fetchone()[0] == "pending"
        assert con.execute("SELECT COUNT(*) FROM gates WHERE project_id=? AND gate=5", (pid,)).fetchone()[0] == 0
