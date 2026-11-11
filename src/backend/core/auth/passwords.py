"""Password hashing, the password rules, and the signed-in account's own password change."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from backend.core.auth.base import ADMIN_ID, LOCK_SECONDS, MAX_FAILURES, AuthError, Forbidden, _account, _event, _failures, _failures_lock
from backend.db import db, now


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${salt.hex()}${hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()}"


def _verify_password(password: str, stored: str) -> bool:
    _, salt, digest = stored.split("$")
    return hmac.compare_digest(hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex(), digest)


_DUMMY_HASH = hash_password(secrets.token_hex(8))


def check_password_rules(password: str) -> None:
    if len(password) < 10:
        raise AuthError("Passwords need at least 10 characters")


def change_password(user_id: str, current: str, new: str, keep_token: str | None) -> None:
    """The environment admin's password lives in the environment. Other sessions of this account end; the current one stays."""
    if user_id == ADMIN_ID:
        raise Forbidden("The administrator's password is set in the environment (ATLAS_ADMIN_PASSWORD). Change it there and restart")
    account = _account(user_id)
    with _failures_lock:  # the same lockout as sign-in, so this form cannot be used to guess the password
        count, until = _failures.get(user_id, (0, 0.0))
        if count >= MAX_FAILURES and time.time() < until:
            raise AuthError("Too many attempts. Try again in a few minutes")
    if not _verify_password(current, account["password_hash"]):
        with _failures_lock:
            _failures[user_id] = (count + 1, time.time() + LOCK_SECONDS)
        _event(user_id, "password.change_failed")
        raise AuthError("The current password is not correct")
    check_password_rules(new)
    keep = hashlib.sha256(keep_token.encode()).hexdigest() if keep_token else ""
    with db() as con:
        con.execute("UPDATE users SET password_hash=?, updated_at=? WHERE id=?", (hash_password(new), now(), user_id))
        con.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (user_id, keep))
    with _failures_lock:
        _failures.pop(user_id, None)
    _event(user_id, "password.changed")
