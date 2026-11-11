"""Sign-in, sign-out, and session lookup."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

from backend.core.auth.base import ADMIN_ID, IDLE_MINUTES, LOCK_SECONDS, MAX_FAILURES, SESSION_HOURS, AuthError, _admin_login, _event, _failures, _failures_lock, _inactive_reason, _lookup
from backend.core.auth.passwords import _DUMMY_HASH, _verify_password
from backend.db import db, now, row


def clock() -> datetime:
    return datetime.now(timezone.utc)  # tests replace this to move time


def login(username: str, password: str) -> str:
    """Returns a session token. Every failure gives the same message, so it does not reveal which accounts exist."""
    key = _lookup(username)
    with _failures_lock:
        count, until = _failures.get(key, (0, 0.0))
        if count >= MAX_FAILURES and time.time() < until:
            raise AuthError("Too many attempts. Try again in a few minutes")
    admin_name, admin_password = _admin_login()
    account = None
    if admin_name and admin_password and hmac.compare_digest(username.strip().lower().encode(), admin_name.encode()):
        ok = hmac.compare_digest(password.encode(), admin_password.encode())
        subject = ADMIN_ID
    else:
        with db() as con:
            account = row(con.execute("SELECT * FROM users WHERE username_lookup=?", (key,)))
        ok = _verify_password(password, account["password_hash"] if account else _DUMMY_HASH) and bool(account)
        subject = account["id"] if account else "unknown"
    if not ok:
        with _failures_lock:
            _failures[key] = (count + 1, time.time() + LOCK_SECONDS)
        _event(subject, "login.failed")
        raise AuthError("The username or password is not correct")
    if account and (reason := _inactive_reason(account)):
        _event(subject, "login.refused")
        raise AuthError(reason)
    with _failures_lock:
        _failures.pop(key, None)
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
    with db() as con:
        con.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), subject, expires, now(), clock().isoformat(timespec="seconds")))
    _event(subject, "login")
    return token


def logout(token: str) -> None:
    with db() as con:
        con.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


def session_user(token: str | None) -> dict | None:
    if not token:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    with db() as con:
        session = row(con.execute("SELECT * FROM sessions WHERE token_hash=?", (digest,)))
        if not session:
            return None
        seen = clock()
        last = datetime.fromisoformat(session["last_seen"]) if session["last_seen"] else seen
        if session["expires_at"] < now() or seen - last > timedelta(minutes=IDLE_MINUTES):
            con.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))
            return None
        if not session["last_seen"] or seen - last >= timedelta(seconds=60):  # ponytail: written once a minute, so a busy page does not write on every request
            con.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (seen.isoformat(timespec="seconds"), digest))
        if session["user_id"] == ADMIN_ID:
            return {"id": ADMIN_ID, "role": "admin", "account_role": "admin"}
        account = row(con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)))
        if not account or _inactive_reason(account):
            con.execute("DELETE FROM sessions WHERE user_id=?", (session["user_id"],))
            return None
    return {"id": account["id"], "role": "user", "account_role": account["role"]}
