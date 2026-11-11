"""Roles: project members, viewer accounts, and project transfer."""
import json

from backend.core import auth
from backend.db import db
from tests.helpers_access import IDS, World, account, world  # noqa: F401 - fixtures
from tests.helpers_api import USER_PASSWORD, client, make_user, sign_in, unique  # noqa: F401 - fixtures


# ---- members ----

def test_removed_member_is_refused_at_once_and_members_see_what_they_should(world):
    pid, member = world.project["id"], world.dev
    assert member.get(f"/api/projects/{pid}").json()["my_role"] == "developer"
    assert pid in [p["id"] for p in member.get("/api/projects").json()]
    assert world.ids["finding_id"] in [f["id"] for f in member.get("/api/findings").json()]
    assert world.ids["approval_id"] in [a["id"] for a in member.get("/api/approvals").json()]
    assert world.ids["doc_id"] in [d["id"] for d in member.get("/api/documents").json()]
    assert world.ids["run_id"] in json.dumps(member.get(f"/api/projects/{pid}/runs").json())
    from backend.maf import observability

    assert world.ids["run_id"] in json.dumps(observability.query(None, None, "", "", 300, "", world.dev_user["id"]), default=str)
    assert member.get("/api/observability/errors").status_code == 200
    assert member.get(f"/api/projects/{pid}/members").status_code == 403, "a member does not see the other members' usernames"
    assert member.post(f"/api/projects/{pid}/members", json={"username": world.stranger_user["username"], "role": "developer"}).status_code == 403
    assert world.owner.get(f"/api/projects/{pid}/members").status_code == 200

    assert world.owner.delete(f"/api/projects/{pid}/members/{world.dev_user['id']}").status_code == 204
    for url in (f"/api/projects/{pid}", f"/api/runs/{world.ids['run_id']}", f"/api/documents/{world.ids['doc_id']}", f"/api/chats/{world.ids['thread_id']}", f"/api/projects/{pid}/overview"):
        assert member.get(url).status_code == 404, url
    assert pid not in [p["id"] for p in member.get("/api/projects").json()]
    assert world.ids["finding_id"] not in [f["id"] for f in member.get("/api/findings").json()]
    assert world.ids["approval_id"] not in [a["id"] for a in member.get("/api/approvals").json()]
    assert world.ids["run_id"] not in json.dumps(observability.query(None, None, "", "", 300, "", world.dev_user["id"]), default=str)
    assert member.post(f"/agui/project-copilot", json={"threadId": world.ids["thread_id"], "messages": []}).status_code == 404


def test_adding_members_answers_only_added_or_not_found(world):
    pid = world.project["id"]
    path = f"/api/projects/{pid}/members"
    missing = world.owner.post(path, json={"username": "nobody.at.all", "role": "developer"})
    own = world.owner.post(path, json={"username": world.owner_user["username"], "role": "developer"})
    admin_name = world.owner.post(path, json={"username": "qa-admin", "role": "developer"})
    assert missing.status_code == own.status_code == admin_name.status_code == 404
    assert missing.json()["message"] == own.json()["message"] == admin_name.json()["message"]
    assert world.owner.post(path, json={"username": world.stranger_user["username"], "role": "owner"}).status_code == 400
    listed = world.owner.get(path).json()
    assert {m["username"] for m in listed} >= {world.dev_user["username"]} and not {world.stranger_user["username"]} & {m["username"] for m in listed}
    assert world.stranger.get("/api/users").status_code == 403, "no list of users for non-admins"
    assert world.owner.delete(f"{path}/{world.stranger_user['id']}").status_code == 404


def test_a_viewer_account_cannot_write_even_as_an_owner_or_developer_member(world):
    pid = world.project["id"]
    assert world.viewer.get(f"/api/projects/{pid}/chats").status_code == 200
    assert world.viewer.post(f"/api/projects/{pid}/chats", json={}).status_code == 403
    assert world.viewer.post(f"/agui/project-copilot", json={"threadId": world.ids["thread_id"], "messages": []}).status_code == 403


def test_transfer_is_admin_only_and_written_to_a_valid_ledger(world):
    pid = world.project["id"]
    assert world.owner.post(f"/api/projects/{pid}/transfer", json={"username": world.dev_user["username"]}).status_code == 403
    assert world.admin.post(f"/api/projects/{pid}/transfer", json={"username": "nobody.at.all"}).status_code == 404
    moved = world.admin.post(f"/api/projects/{pid}/transfer", json={"username": world.dev_user["username"]})
    assert moved.status_code == 200 and moved.json()["owner_id"] == world.dev_user["id"]
    assert world.owner.get(f"/api/projects/{pid}").status_code == 404, "the old owner loses it"
    assert world.dev.get(f"/api/projects/{pid}").json()["my_role"] == "owner"
    with db() as con:
        assert con.execute("SELECT COUNT(*) FROM project_members WHERE project_id=? AND user_id=?", (pid, world.dev_user["id"])).fetchone()[0] == 0
    ledger = world.admin.get(f"/api/projects/{pid}/ledger").json()
    entry = next(e for e in ledger["entries"] if e["action"] == "project.transferred")
    assert entry["actor"] == auth.ADMIN_ID and entry["target"] == world.dev_user["id"] and ledger["verification"]["valid"]
