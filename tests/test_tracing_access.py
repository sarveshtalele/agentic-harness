"""H9 access: a member sees only their own runs, in projects they can see; another member's trace answers 404; the admin sees all."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core import auth, tracing
from backend.db import db
from tests.helpers_api import make_user, sign_in, unique


@pytest.fixture
def admin():
    with TestClient(app) as test_client:  # the lifespan runs tracing.setup()
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client


def _member(admin):
    name = unique("tracer")
    made = make_user(admin, name, role="developer")
    member, response = sign_in(name)
    assert response.status_code == 200, response.text
    return member, made


def _own_trace(client, user_id: str, path: str) -> str:
    """The trace of the request this account just made."""
    assert client.get(path).status_code == 200
    tracing.flush()
    with db() as con:
        return con.execute("SELECT trace_id FROM spans WHERE root=1 AND user_id=? AND name LIKE 'GET %' ORDER BY started_at DESC LIMIT 1", (user_id,)).fetchone()[0]


def _ids(client, **params) -> set[str]:
    answer = client.get("/api/traces", params={"requests": "true", "limit": 200, **params})
    assert answer.status_code == 200, answer.text
    return {item["trace_id"] for item in answer.json()["items"]}


def test_a_member_cannot_read_another_members_trace_and_the_admin_reads_both(admin):
    (alice, alice_user), (bob, bob_user) = _member(admin), _member(admin)
    alice_trace = _own_trace(alice, alice_user["id"], "/api/projects")
    bob_trace = _own_trace(bob, bob_user["id"], "/api/projects")
    assert alice.get(f"/api/traces/{alice_trace}").status_code == 200
    refused = alice.get(f"/api/traces/{bob_trace}")
    assert refused.status_code == 404 and bob_user["id"] not in refused.text
    listed = _ids(alice)
    assert alice_trace in listed and bob_trace not in listed
    assert _ids(alice, user=bob_user["id"]) == set()  # filtering by another account does not widen the scope
    assert alice.get("/api/traces").json()["scope"] == "own"
    assert {alice_trace, bob_trace} <= _ids(admin)
    assert admin.get(f"/api/traces/{bob_trace}").json()["root"]["user_id"] == bob_user["id"]
    assert admin.get("/api/traces").json()["scope"] == "all"


def test_a_members_own_run_in_a_project_they_cannot_see_is_hidden(admin):
    member, member_user = _member(admin)
    hidden = admin.post("/api/projects", json={"name": unique("Hidden")}).json()
    with tracing.new_root("workflow qe", project_id=hidden["id"], user_id=member_user["id"]):
        with tracing.span("stage discover", project_id=hidden["id"]):
            pass
    with tracing.new_root("workflow ba", user_id=member_user["id"]):  # no project: still the member's own run
        with tracing.span("stage draft"):
            pass
    tracing.flush()
    with db() as con:
        found = dict(con.execute("SELECT name, trace_id FROM spans WHERE root=1 AND user_id=? AND name LIKE 'workflow %'", (member_user["id"],)).fetchall())
    assert member.get(f"/api/traces/{found['workflow qe']}").status_code == 404
    assert member.get(f"/api/traces/{found['workflow ba']}").status_code == 200
    assert found["workflow qe"] not in _ids(member) and found["workflow ba"] in _ids(member)
    assert found["workflow qe"] in _ids(admin, project=hidden["id"])


def test_routes_have_rules_and_log_downloads_stay_admin_only(admin):
    member, _ = _member(admin)
    assert auth.rule_of("/api/traces") == "session" and auth.rule_of("/api/traces/abc") == "session"
    assert auth.rule_of("/api/traces/abc/more") is None  # nothing deeper is admitted by default
    assert member.get("/api/logs").status_code == 403
    assert admin.get("/api/logs").status_code in (200, 404)  # 404 only when today has no log file yet
    assert TestClient(app).get("/api/traces").status_code == 401
