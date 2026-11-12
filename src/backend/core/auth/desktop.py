"""Desktop sign-in through the central server (docs/PHASE2_PLAN.md R6, section 12.7).

The server signs a short grant for a signed-in member with its own Ed25519 key (kept encrypted in the settings table):
who they are, their role, and when it ends (ATLAS_DESKTOP_SESSION_DAYS, 7 by default). The desktop app stores only that
grant (encrypted by the OS) and the server's public key, and starts its local backend with both in the environment.
The local backend (desktop profile) refuses to start without a valid grant, mirrors that one member as its only account
with the server's role, and signs the app in when the app posts the same grant. There is no local admin and no local
password; signing out deletes the grant.
ponytail: features (R2) join the grant when governance of features lands (plan step 9).
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend import config
from backend.core.auth.base import ADMIN_ID, AuthError, _account, _event, _lookup
from backend.core.security import decrypt, encrypt
from backend.db import db

SETTING = "desktop_signing_key"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _private_key() -> Ed25519PrivateKey:
    with db() as con:
        found = con.execute("SELECT value FROM settings WHERE key=?", (SETTING,)).fetchone()
        if found and found[0]:
            return Ed25519PrivateKey.from_private_bytes(_unb64(decrypt(found[0].encode())))
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        con.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (SETTING, encrypt(_b64(raw)).decode()))
        return key


def public_key() -> str:
    return _b64(_private_key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def issue(user: dict) -> dict:
    """A grant for the signed-in member, and the key that checks it."""
    if user["id"] == ADMIN_ID:  # the environment admin has no account to mirror; the desktop app never holds admin rights
        raise AuthError("The administrator works in the browser. Sign in to the desktop app with a member account")
    username, role = decrypt(_account(user["id"])["username_enc"].encode()), user["account_role"]
    days = float(os.environ.get("ATLAS_DESKTOP_SESSION_DAYS", "7"))
    claims = {"sub": user["id"], "username": username, "role": role, "iat": int(time.time()), "exp": int(time.time() + days * 86400),
              "nonce": secrets.token_hex(8)}
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    _event(user["id"], "desktop.grant_issued")
    return {"grant": f"{body}.{_b64(_private_key().sign(body.encode()))}", "public_key": public_key(), "expires": claims["exp"]}


def verify(grant: str, key: str) -> dict:
    """The grant's claims, or AuthError when it is forged, damaged or expired."""
    try:
        body, signature = grant.split(".")
        Ed25519PublicKey.from_public_bytes(_unb64(key)).verify(_unb64(signature), body.encode())
        claims = json.loads(_unb64(body))
    except (ValueError, InvalidSignature, json.JSONDecodeError) as exc:
        raise AuthError("The desktop sign-in is not valid. Sign in again") from exc
    if claims.get("exp", 0) <= time.time():
        raise AuthError("The desktop sign-in has ended. Sign in again")
    return claims


def startup_grant() -> dict | None:
    """In the desktop profile, the grant this backend was started with; it will not start without a valid one."""
    if config.PROFILE != "desktop":
        return None
    grant, key = os.environ.get("ATLAS_DESKTOP_GRANT", ""), os.environ.get("ATLAS_DESKTOP_SERVER_KEY", "")
    if not grant or not key:
        raise RuntimeError("The desktop backend starts only after sign-in through the server (ATLAS_DESKTOP_GRANT is missing)")
    return verify(grant, key)


def sign_in(grant: str) -> tuple[str, float]:
    """(local session token, hours left) for the member of the grant this backend was started with; any other is refused."""
    from backend.core.auth.sessions import start_session
    from backend.core.auth.users import create_user

    started = os.environ.get("ATLAS_DESKTOP_GRANT", "")
    if config.PROFILE != "desktop" or not started or not hmac.compare_digest(grant.encode(), started.encode()):
        raise AuthError("This desktop backend was started for another sign-in")
    claims = verify(grant, os.environ["ATLAS_DESKTOP_SERVER_KEY"])
    with db() as con:
        found = con.execute("SELECT id FROM users WHERE username_lookup=?", (_lookup(claims["username"]),)).fetchone()
    if found:
        user_id = found[0]
        with db() as con:
            con.execute("UPDATE users SET role=?, enabled=1 WHERE id=?", (claims["role"], user_id))  # the server's role wins
    else:  # the member's local account: no usable password, so only a server grant signs it in
        user_id = create_user(claims["username"], secrets.token_urlsafe(32) + "!Aa1", role=claims["role"])["id"]
    hours = (claims["exp"] - time.time()) / 3600
    return start_session(user_id, hours=hours, event="desktop.login"), hours
