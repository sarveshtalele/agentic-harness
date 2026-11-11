"""The account page, the idle timeout, and the upgrade from a phase 2 database."""
import logging
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend import db as database
from backend.config import DB_PATH
from backend.core import auth
from backend.db import db
from tests.helpers_access import IDS, World, account, world  # noqa: F401 - fixtures
from tests.helpers_api import USER_PASSWORD, client, make_user, sign_in, unique  # noqa: F401 - fixtures


# ---- account page ----

def test_password_change_works_ends_other_sessions_and_leaves_no_trace(world, caplog):
    name, fresh = unique("changer"), secrets.token_hex(8) + "Zz9!"
    made = make_user(world.admin, name)
    first, _ = sign_in(name)
    second, _ = sign_in(name)
    bad = first.post("/api/account/password", json={"current_password": "wrong-password-1", "new_password": fresh})
    assert bad.status_code == 400 and "current password" in bad.json()["message"]
    assert first.post("/api/account/password", json={"current_password": USER_PASSWORD, "new_password": "short"}).status_code == 400
    with caplog.at_level(logging.DEBUG):
        assert first.post("/api/account/password", json={"current_password": USER_PASSWORD, "new_password": fresh}).status_code == 204
    assert first.get("/api/auth/me").status_code == 200, "the session that changed it stays"
    assert second.get("/api/auth/me").status_code == 401, "other sessions end"
    assert sign_in(name, USER_PASSWORD)[1].status_code == 401
    assert sign_in(name, fresh)[1].status_code == 200
    assert fresh not in caplog.text and USER_PASSWORD not in caplog.text
    with db() as con:
        dump = "\n".join(con.iterdump())
        events = [dict(r) for r in con.execute("SELECT subject, event FROM auth_events WHERE event LIKE 'password.%'")]
    assert fresh not in dump and USER_PASSWORD not in dump and name not in dump
    assert {"subject": made["id"], "event": "password.changed"} in events and {"subject": made["id"], "event": "password.change_failed"} in events


def test_the_environment_admin_cannot_change_its_password_here(world):
    refused = world.admin.post("/api/account/password", json={"current_password": "whatever-it-is", "new_password": "another-long-password"})
    assert refused.status_code == 403 and "environment" in refused.json()["message"]


def test_account_page_data_and_roles_on_the_users_api(world):
    mine = world.dev.get("/api/auth/me").json()
    assert mine["account_role"] == "developer" and "models" in mine and "limits" in mine and "usage" in mine
    changed = world.admin.patch(f"/api/users/{world.stranger_user['id']}", json={"role": "ba"})
    assert changed.status_code == 200 and changed.json()["account_role"] == "ba"
    assert world.admin.patch(f"/api/users/{world.stranger_user['id']}", json={"role": "owner"}).status_code == 400
    assert world.admin.post("/api/users", json={"username": unique("nr"), "password": USER_PASSWORD, "role": "king"}).status_code == 400


# ---- idle timeout ----

def test_session_ends_after_idle_minutes_with_an_injected_clock(world, monkeypatch):
    name = unique("idle")
    make_user(world.admin, name)
    token = auth.login(name, USER_PASSWORD)
    start = datetime.now(timezone.utc)
    at = lambda minutes, seconds=0: monkeypatch.setattr("backend.core.auth.sessions.clock", lambda: start + timedelta(minutes=minutes, seconds=seconds))
    seen = lambda: sqlite3.connect(DB_PATH).execute("SELECT last_seen FROM sessions WHERE token_hash=?", (__import__("hashlib").sha256(token.encode()).hexdigest(),)).fetchone()
    at(0, 30)
    first = seen()
    assert auth.session_user(token) and seen() == first, "a request within a minute does not write"
    at(100)
    assert auth.session_user(token) and seen() != first, "later it does"
    at(100 + auth.IDLE_MINUTES - 1)
    assert auth.session_user(token)
    at(100 + 2 * auth.IDLE_MINUTES)
    assert auth.session_user(token) is None and seen() is None, "idle too long: gone, and deleted"


# ---- upgrade from phase 2 ----

def test_migration_010_keeps_users_and_sessions_from_a_phase_2_database(tmp_path, monkeypatch):
    path = tmp_path / "phase2.sqlite3"
    monkeypatch.setattr(database, "DB_PATH", path)
    con = sqlite3.connect(path)
    for sql in sorted(database.MIGRATIONS.glob("*.sql")):
        if int(sql.name.split("_")[0]) <= 9:
            con.executescript(sql.read_text(encoding="utf-8"))
    con.execute("PRAGMA user_version=9")
    stamp, later = database.now(), (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(timespec="seconds")
    con.execute("INSERT INTO users (id, username_lookup, username_enc, password_hash, enabled, created_at, updated_at) VALUES ('usr_old','k','e','h',1,?,?)", (stamp, stamp))
    con.execute("INSERT INTO projects (id, name, created_at, updated_at, owner_id) VALUES ('p1','P',?,?,'usr_old')", (stamp, stamp))
    con.execute("INSERT INTO sessions VALUES ('tok','usr_old',?,?)", (later, stamp))
    con.commit()
    con.close()

    database.migrate()
    con = sqlite3.connect(path)
    assert con.execute("SELECT role FROM users WHERE id='usr_old'").fetchone()[0] == "developer"
    assert con.execute("SELECT COUNT(*) FROM project_members").fetchone()[0] == 0
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(list(database.MIGRATIONS.glob("*.sql")))
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE users SET role='king'")
    con.close()
    old = {"id": "usr_old", "role": "user", "account_role": "developer"}
    assert auth.can_write("p1", old) and auth.project_role("p1", old) == "owner", "the old owner keeps everything"
    import hashlib

    con = sqlite3.connect(path)
    con.execute("UPDATE sessions SET token_hash=? WHERE token_hash='tok'", (hashlib.sha256(b"old-token").hexdigest(),))
    con.commit()
    con.close()
    assert auth.session_user("old-token")["account_role"] == "developer", "a session with no last_seen still works and gets one"
