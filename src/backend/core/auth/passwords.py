"""Password hashing, the password rules, and the signed-in account's own password change."""
from __future__ import annotations

import functools
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from backend.core.auth.base import ADMIN_ID, LOCK_SECONDS, MAX_FAILURES, AuthError, Forbidden, _account, _event, _failures, _failures_lock
from backend.core.security import register_secret
from backend.db import db, now

MIN_LENGTH = 12
# ponytail: the most common breached passwords of 12+ characters; a full list (e.g. a Have I Been Pwned download, one per
# line) can be named with ATLAS_BREACHED_PASSWORDS_FILE.
COMMON = {"123456789012", "1234567890123", "12345678901234", "123456789123", "password1234", "password12345",
          "password123456", "qwertyuiop12", "qwertyuiop123", "qwerty123456", "1q2w3e4r5t6y", "1qaz2wsx3edc",
          "abcdefghijkl", "abcd12345678", "iloveyou1234", "welcome12345", "letmein12345", "administrator",
          "aaaaaaaaaaaa", "000000000000", "111111111111", "qwertyuiopas", "asdfghjklzxc", "zaq12wsxcde3",
          "passwordpassword", "changeme1234", "football1234", "baseball1234", "monkey123456", "superman1234"}


def _cost() -> int:
    """scrypt N; raising ATLAS_SCRYPT_N makes each account rehash at its next sign-in."""
    return int(os.environ.get("ATLAS_SCRYPT_N", str(2**14)))


def _pepper() -> bytes:
    """A server-side secret mixed into every hash (Key Vault on Azure), so a stolen database alone cannot be cracked."""
    pepper = os.environ.get("ATLAS_PASSWORD_PEPPER", "")
    register_secret(pepper)
    return pepper.encode()


def _pepper_id(pepper: bytes) -> str:
    return hashlib.sha256(pepper).hexdigest()[:8] if pepper else "-"


def _digest(password: str, salt: bytes, n: int, pepper: bytes) -> str:
    material = hmac.new(pepper, password.encode(), hashlib.sha256).digest() if pepper else password.encode()
    return hashlib.scrypt(material, salt=salt, n=n, r=8, p=1, maxmem=256 * n * 8 + 2**20).hex()


def hash_password(password: str) -> str:
    """`scrypt$N$pepper-id$salt$digest`. The pepper itself is never stored, only which one was used."""
    salt, n, pepper = secrets.token_bytes(16), _cost(), _pepper()
    return f"scrypt${n}${_pepper_id(pepper)}${salt.hex()}${_digest(password, salt, n, pepper)}"


def _verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 3:  # before pepper and cost were recorded: N=2**14, no pepper
        _, salt, digest = parts
        return hmac.compare_digest(_digest(password, bytes.fromhex(salt), 2**14, b""), digest)
    _, n, pid, salt, digest = parts
    pepper = _pepper()
    if pid != _pepper_id(pepper if pid != "-" else b""):
        return False  # hashed with a pepper this server no longer has
    return hmac.compare_digest(_digest(password, bytes.fromhex(salt), int(n), pepper if pid != "-" else b""), digest)


def needs_rehash(stored: str) -> bool:
    """True when the hash predates the current cost or pepper; sign-in then stores a fresh one."""
    parts = stored.split("$")
    return len(parts) != 5 or int(parts[1]) != _cost() or parts[2] != _pepper_id(_pepper())


_DUMMY_HASH = hash_password(secrets.token_hex(8))


@functools.cache
def _breached_file(path: str) -> frozenset[str]:
    return frozenset(line.strip().lower() for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())


def check_password_rules(password: str, username: str = "") -> None:
    if len(password) < MIN_LENGTH:
        raise AuthError(f"Passwords need at least {MIN_LENGTH} characters")
    lowered = password.lower()
    if username and username.strip().lower() in lowered:
        raise AuthError("The password must not contain the username")
    listed = os.environ.get("ATLAS_BREACHED_PASSWORDS_FILE", "")
    if lowered in COMMON or len(set(lowered)) <= 2 or (listed and Path(listed).is_file() and lowered in _breached_file(listed)):
        raise AuthError("This password appears in lists of breached passwords. Choose another")


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
