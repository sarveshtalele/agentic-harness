"""Sign-in, sessions, isolation and per-user limits."""

import json
import os
import re
import secrets

import pytest

from fastapi.testclient import TestClient

from backend.app import app
from backend.maf import llm

from tests.scripted_client import ScriptedClient
from tests.helpers_api import CALC, client, make_user, project, sign_in, unique, upload_repo, USER_PASSWORD  # noqa: F401 - fixtures


def test_every_route_needs_a_session():
    public = {"/api/health", "/api/auth/login", "/api/auth/status", "/api/auth/desktop", "/api/mcp/oauth/callback"}  # desktop: a signed grant instead of a session (test_desktop_signin.py)
    anonymous = TestClient(app)
    checked = 0
    for path, methods in app.openapi()["paths"].items():
        if not path.startswith(("/api/", "/agui/")) or path in public:
            continue
        url = re.sub(r"\{[^}]+\}", "x", path)
        for method in methods:
            assert anonymous.request(method.upper(), url).status_code == 401, f"{method} {path} is open"
            checked += 1
    assert checked > 60


def test_login_failures_are_uniform_and_lock_out(client):
    name = unique()
    make_user(client, name)
    wrong_value = secrets.token_hex(8)
    _, wrong = sign_in(name, wrong_value)
    _, absent = sign_in(unique("ghost"), wrong_value)
    assert wrong.status_code == absent.status_code == 401 and {**wrong.json(), "error_id": ""} == {**absent.json(), "error_id": ""}  # every error response has its own id
    for _ in range(5):
        sign_in(name, wrong_value)
    _, locked = sign_in(name)
    assert locked.status_code == 401 and "Too many attempts" in locked.json()["detail"]


def test_session_cookie_is_protected_and_logout_ends_it(client):
    name = unique()
    make_user(client, name)
    other, response = sign_in(name)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert other.get("/api/auth/me").json()["username"] == name
    saved = dict(other.cookies)
    other.post("/api/auth/logout")
    assert TestClient(app, cookies=saved).get("/api/auth/me").status_code == 401


def test_passwords_and_usernames_never_reach_storage_or_logs(client, caplog):
    import logging

    from backend.core.security import redact
    from tests.helpers_db import dump as dump_tables

    name = unique("secretname")
    user = make_user(client, name)
    typed, field = secrets.token_hex(8), "password"
    admin_value = os.environ["ATLAS_ADMIN_PASSWORD"]
    with caplog.at_level(logging.DEBUG):
        sign_in(name)
        sign_in(name, typed)
        logging.getLogger("uvicorn.access").warning('body {"%s": "%s"} and %s=%s', field, typed, field, typed)
    logged = caplog.text
    assert typed not in logged and USER_PASSWORD not in logged and name not in logged
    dump = dump_tables()
    assert USER_PASSWORD not in dump and name not in dump and admin_value not in dump
    assert "password" not in json.dumps(user) and USER_PASSWORD not in json.dumps(client.get("/api/users").json())
    assert admin_value not in redact(f"it leaked: {admin_value}")
    assert client.get("/api/auth/events").json() and name not in json.dumps(client.get("/api/auth/events").json())


def test_users_see_only_their_own_projects(client):
    name = unique()
    make_user(client, name)
    other, _ = sign_in(name)
    admin_project = client.post("/api/projects", json={"name": "Admin only", "description": ""}).json()
    upload_repo(client, admin_project, CALC)
    doc = client.post(f"/api/projects/{admin_project['id']}/documents", json={"kind": "brd", "title": "Private", "content": "# T\n"}).json()
    mine = other.post("/api/projects", json={"name": "Mine", "description": ""}).json()
    assert [p["id"] for p in other.get("/api/projects").json()] == [mine["id"]]
    for path in (f"/api/projects/{admin_project['id']}", f"/api/projects/{admin_project['id']}/repo", f"/api/documents/{doc['id']}", f"/api/documents/{doc['id']}/export/md"):
        assert other.get(path).status_code == 404, path
    assert other.delete(f"/api/projects/{admin_project['id']}?confirm=x").status_code == 404
    assert not [d for d in other.get("/api/documents").json() if d["id"] == doc["id"]]
    assert not other.get(f"/api/observability?project_id={admin_project['id']}").json()["items"]
    assert {p["id"] for p in client.get("/api/projects").json()} >= {admin_project["id"], mine["id"]}, "the admin sees all"
    for path, method in (("/api/users", "GET"), ("/api/connections", "GET"), ("/api/agents/guardrail-events", "GET"), (f"/api/projects/{mine['id']}/repo/local", "POST")):
        assert other.request(method, path, json={"path": "/etc"}).status_code == 403, path
    assert other.put("/api/settings/llm", json={"base_url": "https://evil.example"}).status_code == 403
    assert "base_url" not in other.get("/api/settings/llm").json()


def test_allocation_dates_and_model_limit_a_users_work(client):
    from backend.core import auth
    from backend.db import db, now
    from backend.maf import runtime

    name = unique()
    user = make_user(client, name, model="small-model", token_limit=100)
    other, _ = sign_in(name)
    project = other.post("/api/projects", json={"name": "Limited", "description": ""}).json()
    assert auth.model_for(project["id"]) == "small-model" and other.get("/api/settings/llm").json()["model"] == "small-model"
    auth.check_allowance(project["id"])
    with db() as con:
        con.execute("INSERT INTO agent_calls (agent, project_id, source, prompt_ref, tokens_in, tokens_out, latency_ms, tool_calls, status, created_at, user_id) VALUES ('project-copilot', ?, 'chat', 'x', 80, 30, 1, 0, 'ok', ?, ?)", (project["id"], now(), user["id"]))
    assert other.get("/api/auth/me").json()["tokens_used"] == 110
    llm.set_client_override(ScriptedClient([("x", "ok")]))
    with pytest.raises(auth.AllowanceError, match="allocation"):
        runtime.AgentCall(None, project["id"], "project-copilot")
    client.patch(f"/api/users/{user['id']}", json={"token_limit": 1000})
    auth.check_allowance(project["id"])
    client.patch(f"/api/users/{user['id']}", json={"active_until": "2020-01-01"})
    assert other.get("/api/projects").status_code == 401, "an expired account loses its session"
    with pytest.raises(auth.AllowanceError):
        runtime.AgentCall(None, project["id"], "project-copilot")
    _, refused = sign_in(name)
    assert refused.status_code == 401 and "ended" in refused.json()["detail"]
    assert client.patch(f"/api/users/{user['id']}", json={"active_from": "2030-01-01", "active_until": "2029-01-01"}).status_code == 400


def test_new_password_and_disable_end_sessions(client):
    name = unique()
    user = make_user(client, name)
    other, _ = sign_in(name)
    assert client.post("/api/users", json={"username": unique(), "password": "short"}).status_code == 400
    assert client.post("/api/users", json={"username": name, "password": USER_PASSWORD}).status_code == 400
    replacement = secrets.token_urlsafe(15)
    client.patch(f"/api/users/{user['id']}", json={"password": replacement})
    assert other.get("/api/projects").status_code == 401
    _, old = sign_in(name)
    assert old.status_code == 401
    fresh, ok = sign_in(name, replacement)
    assert ok.status_code == 200
    client.patch(f"/api/users/{user['id']}", json={"enabled": False})
    assert fresh.get("/api/projects").status_code == 401
