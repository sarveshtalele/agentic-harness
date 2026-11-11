"""Account email: stored encrypted, shown only to the admin and the owner, and carried on approvals."""

from backend.config import LOGS
from backend.core import auth
from backend.db import db
from tests.helpers_access import account, world  # noqa: F401 - fixtures
from tests.helpers_api import client, make_user, project, unique  # noqa: F401 - fixtures


def _mail(prefix):
    return f"{unique(prefix)}@example.org"


def test_email_is_stored_encrypted_and_visible_by_rule(client):
    mine, theirs = _mail("a"), _mail("b")
    one, rec_one = account(client)
    two, rec_two = account(client)
    assert one.patch("/api/account/email", json={"email": mine}).json()["email"] == mine
    assert two.patch("/api/account/email", json={"email": theirs}).status_code == 200
    with db() as con:
        raw = con.execute("SELECT email_enc FROM users WHERE id=?", (rec_one["id"],)).fetchone()[0]
    assert raw and mine not in raw
    assert one.get("/api/auth/me").json()["email"] == mine
    listed = {u["id"]: u["email"] for u in client.get("/api/users").json()}
    assert listed[rec_one["id"]] == mine and listed[rec_two["id"]] == theirs
    assert theirs not in one.get("/api/auth/me").text
    assert one.get("/api/users").status_code == 403
    details = auth.approver_details({rec_two["id"]})  # viewed with no signed-in user: name only
    assert details[rec_two["id"]]["email"] == ""


def test_admin_creates_and_edits_with_email_and_invalid_is_422(client):
    name, mail = unique("mk"), _mail("c")
    made = make_user(client, name, email=mail)
    assert made["email"] == mail
    assert client.patch(f"/api/users/{made['id']}", json={"email": ""}).json()["email"] == ""
    assert client.patch(f"/api/users/{made['id']}", json={"email": "not-an-email"}).status_code == 422
    assert client.patch(f"/api/users/{made['id']}", json={"email": "a@b.co" + "x" * 260}).status_code == 422
    other, _ = account(client)
    assert other.patch("/api/account/email", json={"email": "bad@"}).status_code == 422
    assert client.patch("/api/account/email", json={"email": mail}).status_code == 400  # the env admin has no row


def test_admin_approval_shows_name_role_and_env_email(client, project, monkeypatch):
    monkeypatch.setenv("ATLAS_ADMIN_EMAIL", mail := _mail("admin"))
    pid = project["id"]
    assert client.post(f"/api/projects/{pid}/gates/0/decision", json={"approved": True}).status_code == 200
    gate = client.get(f"/api/projects/{pid}/gates").json()[0]
    assert gate["decided_by"] == "admin" and gate["decided_by_name"] == "Administrator" and gate["decided_by_email"] == mail
    assert gate["decided_by_role"] == "administrator"
    owner, _ = account(client)
    owner_project = owner.post("/api/projects", json={"name": unique("p")}).json()
    client.post(f"/api/projects/{owner_project['id']}/gates/0/decision", json={"approved": True})
    seen = owner.get(f"/api/projects/{owner_project['id']}/gates").json()[0]
    from backend.db import new_id, now
    run, apr = new_id("run"), new_id("apr")
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, started_at) VALUES (?,?,?,?,?,?)", (run, pid, "ba", "completed", "{}", now()))
        con.execute("INSERT INTO approvals (id, run_id, project_id, title, summary, status, decided_by, created_at) VALUES (?,?,?,?,?,?,?,?)", (apr, run, pid, "T", "S", "approved", "admin", now()))
    listed = client.get(f"/api/projects/{pid}/approvals?status=approved").json()
    assert listed[0]["decided_by_name"] == "Administrator" and listed[0]["decided_by_email"] == mail
    assert seen["decided_by_name"] == "Administrator" and seen["decided_by_email"] == "" and mail not in str(seen)


def test_no_email_reaches_the_logs(client):
    mail = _mail("logcheck")
    one, _ = account(client)
    one.patch("/api/account/email", json={"email": mail})
    one.patch("/api/account/email", json={"email": mail.replace("@", "")})  # a rejected one too
    client.get("/api/users")
    assert not any(mail in f.read_text(encoding="utf-8", errors="ignore") for f in LOGS.glob("*") if f.is_file())
