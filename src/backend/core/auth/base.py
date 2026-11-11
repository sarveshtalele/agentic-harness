"""Auth constants, the shared failure counter, errors, and small helpers every other auth module builds on."""
from __future__ import annotations

import hashlib
import hmac
import os
import threading
from contextvars import ContextVar
from datetime import datetime, timezone

from backend.core.security import encryption_key, register_secret
from backend.db import db, now, row

ADMIN_ID = "admin"
COOKIE = "aqe_session"
SESSION_HOURS = int(os.environ.get("ATLAS_SESSION_HOURS", "12"))
IDLE_MINUTES = int(os.environ.get("ATLAS_SESSION_IDLE_MINUTES", "480"))
ROLES = ("qe_lead", "ba", "developer", "viewer")
ROLE_NAMES = {"admin": "administrator", "qe_lead": "QE lead", "ba": "BA", "developer": "developer", "viewer": "viewer"}
MAX_FAILURES = 5
LOCK_SECONDS = 300
EVAL_PROJECT = "prj_agent_evals"
current_user: ContextVar[dict | None] = ContextVar("current_user", default=None)
_failures: dict[str, tuple[int, float]] = {}  # ponytail: one process. Move to the database before running several instances
_failures_lock = threading.Lock()


class AuthError(ValueError):
    pass


class Forbidden(AuthError):
    """The signed-in account is known but its role does not allow this. Answered 403 with the message."""


def _admin_login() -> tuple[str, str]:
    username, password = os.environ.get("ATLAS_ADMIN_USERNAME", ""), os.environ.get("ATLAS_ADMIN_PASSWORD", "")
    register_secret(password)
    return username.strip().lower(), password


def admin_configured() -> bool:
    return all(_admin_login())


def _lookup(username: str) -> str:
    return hmac.new(encryption_key(), username.strip().lower().encode(), hashlib.sha256).hexdigest()


def _event(subject: str, event: str) -> None:
    with db() as con:
        con.execute("INSERT INTO auth_events (subject, event, created_at) VALUES (?,?,?)", (subject, event, now()))


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _inactive_reason(user: dict) -> str:
    if not user["enabled"]:
        return "This account is disabled"
    if user["active_from"] and _today() < user["active_from"]:
        return f"This account starts on {user['active_from']}"
    if user["active_until"] and _today() > user["active_until"]:
        return f"This account ended on {user['active_until']}"
    return ""


def signer() -> str:
    """The signed-in account's id: the only identity written to the ledger, gates, and versions. Never taken from a request body."""
    user = current_user.get()
    if not user:
        raise AuthError("Sign in first")
    return user["id"]


def _account(user_id: str | None) -> dict | None:
    """The limited account for an id, or None for the administrator and for work with no account behind it."""
    if not user_id or user_id == ADMIN_ID:
        return None
    with db() as con:
        return row(con.execute("SELECT * FROM users WHERE id=?", (user_id,)))


def check_role(role: str) -> None:
    if role not in ROLES:
        raise AuthError(f"A role is one of: {', '.join(ROLES)}")
