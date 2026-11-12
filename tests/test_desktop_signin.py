"""Desktop sign-in through the server (docs/PHASE2_PLAN.md R6, 12.7): signed grants, the desktop backend's start gate,
the one mirrored member, and no local admin or password."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.app import app
from backend.core import auth
from backend.core.auth import desktop
from tests.helpers_api import USER_PASSWORD, client, make_user, unique  # noqa: F401 - fixtures


def _signed(claims):
    body = desktop._b64(json.dumps(claims).encode())
    return f"{body}.{desktop._b64(desktop._private_key().sign(body.encode()))}"


def test_the_server_signs_a_grant_for_a_member_and_not_for_the_admin(client):
    name = unique("desk")
    member = make_user(client, name)
    with TestClient(app) as other:
        assert other.post("/api/auth/login", json={"username": name, "password": USER_PASSWORD}).status_code == 200
        made = other.post("/api/auth/desktop-session").json()
    claims = desktop.verify(made["grant"], made["public_key"])
    assert (claims["sub"], claims["username"], claims["role"]) == (member["id"], name, "developer") and claims["exp"] > time.time() + 6 * 86400
    body, signature = made["grant"].split(".")
    forged = desktop._b64(json.dumps({**claims, "role": "qe_lead"}).encode())
    for bad in (f"{forged}.{signature}", made["grant"][:-2], "nonsense"):
        with pytest.raises(auth.AuthError, match="not valid"):
            desktop.verify(bad, made["public_key"])
    with pytest.raises(auth.AuthError, match="ended"):
        desktop.verify(_signed({**claims, "exp": int(time.time()) - 1}), made["public_key"])
    assert client.post("/api/auth/desktop-session").status_code == 403  # the environment admin never gets a desktop grant
    assert TestClient(app).post("/api/auth/desktop-session").status_code == 401


def test_the_desktop_backend_signs_in_only_the_member_it_was_started_for(client, monkeypatch):
    name = unique("deskonly")
    grant = _signed({"sub": "usr_server", "username": name, "role": "ba", "iat": int(time.time()), "exp": int(time.time()) + 3600, "nonce": "a"})
    monkeypatch.setattr(config, "PROFILE", "desktop")
    monkeypatch.delenv("ATLAS_DESKTOP_GRANT", raising=False)
    with pytest.raises(RuntimeError, match="sign-in through the server"):
        desktop.startup_grant()
    monkeypatch.setenv("ATLAS_DESKTOP_GRANT", grant)
    monkeypatch.setenv("ATLAS_DESKTOP_SERVER_KEY", desktop.public_key())
    assert desktop.startup_grant()["username"] == name
    local = TestClient(app)
    other = _signed({"sub": "usr_x", "username": unique("intruder"), "role": "qe_lead", "iat": 0, "exp": int(time.time()) + 3600, "nonce": "b"})
    assert local.post("/api/auth/desktop", json={"grant": other}).status_code == 401
    signed_in = local.post("/api/auth/desktop", json={"grant": grant})
    assert signed_in.status_code == 200 and auth.COOKIE in signed_in.cookies
    me = local.get("/api/auth/me").json()
    assert me["username"] == name and me["account_role"] == "ba" and me["role"] != "admin"  # the server's role, never admin
    assert local.post("/api/auth/login", json={"username": name, "password": "anything-at-all-1"}).status_code in (401, 503)
    assert local.get("/api/auth/status").json()["desktop"] is True
