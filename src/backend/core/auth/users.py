"""Account records: create, read, update, list, and the audit events."""
from __future__ import annotations

import re

from backend.core import models
from backend.core.auth.base import ADMIN_ID, ROLE_NAMES, AuthError, admin_email, _admin_login, _event, _inactive_reason, _lookup, check_role, current_user
from backend.core.auth.passwords import check_password_rules, hash_password
from backend.core.security import decrypt, encrypt
from backend.db import db, new_id, now, row, rows


def tokens_used(user_id: str) -> int:
    """Everything the account started, whichever project it ran in."""
    return models.used(user_id)


def display_names(ids: set[str]) -> dict[str, str]:
    """Account id to a name for this viewer. A username is a login detail, so only its owner and the admin see it."""
    viewer = current_user.get() or {}
    names = {}
    for found in ids:
        if found == ADMIN_ID:
            names[found] = "Administrator"
        elif found.startswith("usr_") and (viewer.get("role") == "admin" or viewer.get("id") == found):
            try:
                names[found] = get_user(found)["username"]
            except KeyError:
                pass
    return names


EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def check_email(email: str | None) -> str:
    email = (email or "").strip()
    if email and (len(email) > 254 or not EMAIL.fullmatch(email)):
        raise AuthError("That email address is not valid")
    return email


def _email(account: dict) -> str:
    return decrypt(account["email_enc"].encode()) if account.get("email_enc") else ""


def approver_details(ids: set[str]) -> dict[str, dict]:
    """Account id to {id, name, role, email}. The email follows display_names: the admin sees all, a member sees their own, nobody else's."""
    viewer = current_user.get() or {}
    names = display_names(ids)
    found = {}
    for one in ids:
        detail = {"id": one, "name": names.get(one, one), "role": "", "email": ""}
        if one == ADMIN_ID:
            detail["role"] = ROLE_NAMES["admin"]
            detail["email"] = admin_email() if viewer.get("role") == "admin" or viewer.get("id") == ADMIN_ID else ""
        elif one.startswith("usr_"):
            try:
                account = get_user(one)
            except KeyError:
                account = None
            if account:
                detail["role"] = ROLE_NAMES.get(account["account_role"], account["account_role"])
                detail["email"] = account["email"] if viewer.get("role") == "admin" or viewer.get("id") == one else ""
        found[one] = detail
    return found


def named(items: list[dict], key: str = "decided_by") -> list[dict]:
    """Adds decided_by_name, decided_by_role and decided_by_email beside the stored id, which stays."""
    details = approver_details({i[key] for i in items if i.get(key)})
    return [{**i, f"{key}_name": (details.get(i.get(key)) or {}).get("name", i.get(key)), f"{key}_role": (details.get(i.get(key)) or {}).get("role", ""), f"{key}_email": (details.get(i.get(key)) or {}).get("email", "")} for i in items]


def set_email(user_id: str, email: str | None) -> dict:
    email = check_email(email)
    with db() as con:
        if not con.execute("UPDATE users SET email_enc=?, updated_at=? WHERE id=?", (encrypt(email).decode() if email else "", now(), user_id)).rowcount:
            raise AuthError("The admin email is set with ATLAS_ADMIN_EMAIL in .env")
    _event(user_id, "user.email_changed")
    return get_user(user_id)


def _public(account: dict) -> dict:
    uid = account["id"]
    limits = models.limits(uid)
    return {"id": uid, "username": decrypt(account["username_enc"].encode()), "email": _email(account), "role": "user", "account_role": account["role"], "model": account["model"], "models": models.ticked(uid), "token_limit": account["token_limit"], "tokens_used": tokens_used(uid),
            "limits": {p: next((i["tokens"] for i in limits if not i["model"] and i["period"] == p), None) for p in models.PERIODS}, "model_limits": [i for i in limits if i["model"]],
            "usage": models.usage(uid), "model_usage": {i["model"]: models.used(uid, models.bounds(i["period"])[0], i["model"]) for i in limits if i["model"]},
            "active_from": account["active_from"], "active_until": account["active_until"], "enabled": bool(account["enabled"]), "status": _inactive_reason(account) or "Active", "created_at": account["created_at"]}


def describe(user: dict) -> dict:
    if user["role"] == "admin":
        return {"id": ADMIN_ID, "username": _admin_login()[0], "email": admin_email(), "role": "admin", "account_role": "admin", "model": "", "models": [], "token_limit": None, "tokens_used": tokens_used(ADMIN_ID), "limits": {}, "model_limits": [], "usage": None,
                "active_from": None, "active_until": None, "enabled": True, "status": "Active"}
    with db() as con:
        return _public(row(con.execute("SELECT * FROM users WHERE id=?", (user["id"],))))


def _check_dates(active_from: str | None, active_until: str | None) -> None:
    if active_from and active_until and active_until < active_from:
        raise AuthError("The end date is before the start date")


def create_user(username: str, password: str, model: str = "", token_limit: int | None = None, active_from: str | None = None, active_until: str | None = None, allowed_models: list[str] | None = None, role: str = "developer", email: str | None = None) -> dict:
    username = username.strip()
    email = check_email(email)
    check_role(role)
    if not re.fullmatch(r"[\w.@-]{3,60}", username):
        raise AuthError("Usernames need 3 to 60 letters, numbers, dots, dashes, or @")
    if username.lower() == _admin_login()[0]:
        raise AuthError("That username is not available")
    check_password_rules(password)
    _check_dates(active_from, active_until)
    allowed_models = allowed_models if allowed_models is not None else ([model.strip()] if model.strip() else [])
    try:
        model = models.check_allowed(allowed_models, model.strip())
    except ValueError as exc:
        raise AuthError(str(exc)) from exc
    with db() as con:
        if con.execute("SELECT 1 FROM users WHERE username_lookup=?", (_lookup(username),)).fetchone():
            raise AuthError("That username is not available")
        user_id = new_id("usr")
        con.execute("INSERT INTO users (id, username_lookup, username_enc, password_hash, model, token_limit, active_from, active_until, enabled, created_at, updated_at, role, email_enc) VALUES (?,?,?,?,?,?,?,?,1,?,?,?,?)",
                    (user_id, _lookup(username), encrypt(username).decode(), hash_password(password), model.strip(), token_limit, active_from or None, active_until or None, now(), now(), role, encrypt(email).decode() if email else ""))
    models.set_allowed(user_id, allowed_models, model)
    _event(user_id, "user.created")
    return get_user(user_id)


def get_user(user_id: str) -> dict:
    with db() as con:
        account = row(con.execute("SELECT * FROM users WHERE id=?", (user_id,)))
    if not account:
        raise KeyError(user_id)
    return _public(account)


def list_users() -> list[dict]:
    with db() as con:
        return [_public(u) for u in rows(con.execute("SELECT * FROM users ORDER BY created_at DESC"))]


def update_user(user_id: str, changes: dict) -> dict:
    """Changes only the fields given. A new password or a disabled account ends that user's sessions."""
    current_user_record = get_user(user_id)
    fields = {k: changes[k] for k in ("model", "token_limit", "active_from", "active_until", "enabled", "role") if k in changes}
    if "role" in fields:
        check_role(fields["role"])
    if "models" in changes or "model" in changes:  # the default is always one of the ticked models
        names = changes["models"] if "models" in changes else current_user_record["models"]
        wanted = changes["model"] if "model" in changes else (current_user_record["model"] if current_user_record["model"] in names else "")
        try:
            fields["model"] = models.check_allowed(names, wanted)
        except ValueError as exc:
            raise AuthError(str(exc)) from exc
    if "email" in changes:
        email = check_email(changes["email"])
        fields["email_enc"] = encrypt(email).decode() if email else ""
    if changes.get("password"):
        check_password_rules(changes["password"])
        fields["password_hash"] = hash_password(changes["password"])
    with db() as con:
        current = row(con.execute("SELECT active_from, active_until FROM users WHERE id=?", (user_id,)))
        _check_dates(fields.get("active_from", current["active_from"]), fields.get("active_until", current["active_until"]))
        for name, value in fields.items():
            stored = int(value) if name == "enabled" else (value or None) if name in {"active_from", "active_until"} else value
            con.execute(f"UPDATE users SET {name}=?, updated_at=? WHERE id=?", (stored, now(), user_id))  # names come from the fixed list above
        if "password_hash" in fields or fields.get("enabled") is False:
            con.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    try:
        if "models" in changes:
            models.set_allowed(user_id, changes["models"], fields["model"])
        if "limits" in changes or "model_limits" in changes:
            models.set_limits(user_id, changes.get("limits"), changes.get("model_limits"))
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthError(f"Limits or models not saved: {exc}") from exc
    _event(user_id, "user.updated")
    return get_user(user_id)


def recent_events(limit: int = 50) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT * FROM auth_events ORDER BY id DESC LIMIT ?", (limit,)))
