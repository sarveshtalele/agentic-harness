"""Project roles, members, ownership transfer, and the project-visibility SQL."""
from __future__ import annotations

from backend.core import ledger
from backend.core.auth.base import EVAL_PROJECT, _account, _lookup, check_role, current_user, signer
from backend.core.security import decrypt
from backend.db import db, now, rows


def _member_role(project_id: str, user_id: str) -> str | None:
    with db() as con:
        found = con.execute("SELECT role FROM project_members WHERE project_id=? AND user_id=?", (project_id, user_id)).fetchone()
    return found[0] if found else None


def project_role(project_id: str | None, user: dict | None = None) -> str | None:
    """'admin', 'owner', the member's role, or None when the project is not theirs to see."""
    user = user or current_user.get()
    if not user:
        return None
    if user["role"] == "admin":
        return "admin"
    if not project_id or project_id == EVAL_PROJECT:
        return None
    with db() as con:
        found = con.execute("SELECT owner_id FROM projects WHERE id=?", (project_id,)).fetchone()
    if not found:
        return None
    return "owner" if found[0] == user["id"] else _member_role(project_id, user["id"])


def can_see_project(project_id: str | None, user: dict | None = None) -> bool:
    return project_role(project_id, user) is not None


def can_write(project_id: str | None, user: dict | None = None) -> bool:
    """The lesser of the account role and the member role: a viewer on either side cannot write."""
    user = user or current_user.get()
    role = project_role(project_id, user)
    return bool(role) and user["account_role"] != "viewer" and role != "viewer"


def _id_for(username: str) -> str | None:
    with db() as con:
        found = con.execute("SELECT id FROM users WHERE username_lookup=?", (_lookup(username),)).fetchone()
    return found[0] if found else None


def members(project_id: str) -> list[dict]:
    with db() as con:
        found = rows(con.execute("SELECT user_id, role, created_at FROM project_members WHERE project_id=? ORDER BY created_at", (project_id,)))
    return [{**m, "username": decrypt(_account(m["user_id"])["username_enc"].encode())} for m in found]


def add_member(project_id: str, username: str, role: str) -> dict:
    """The owner types the exact username. The only answers are added, or no such account."""
    check_role(role)
    user_id = _id_for(username)
    with db() as con:
        owner = con.execute("SELECT owner_id FROM projects WHERE id=?", (project_id,)).fetchone()
        if not user_id or (owner and owner[0] == user_id):
            raise KeyError("No account has that username")  # the owner themself gets the same answer, so there is one message
        con.execute("INSERT OR REPLACE INTO project_members VALUES (?,?,?,?,?)", (project_id, user_id, role, signer(), now()))
    ledger.append(project_id, signer(), "member.added", user_id, {"role": role})
    return {"user_id": user_id, "role": role}


def remove_member(project_id: str, user_id: str) -> None:
    with db() as con:
        gone = con.execute("DELETE FROM project_members WHERE project_id=? AND user_id=?", (project_id, user_id)).rowcount
    if not gone:
        raise KeyError(user_id)
    ledger.append(project_id, signer(), "member.removed", user_id)


def transfer_project(project_id: str, username: str) -> dict:
    user_id = _id_for(username)
    if not user_id:
        raise KeyError("No account has that username")
    with db() as con:
        old = con.execute("SELECT owner_id FROM projects WHERE id=?", (project_id,)).fetchone()[0]
        con.execute("UPDATE projects SET owner_id=?, updated_at=? WHERE id=?", (user_id, now(), project_id))
        con.execute("DELETE FROM project_members WHERE project_id=? AND user_id=?", (project_id, user_id))
    ledger.append(project_id, signer(), "project.transferred", user_id, {"from": old, "to": user_id})
    return {"owner_id": user_id}


# ponytail: SQL for "projects this account can see", used where the log is filtered in the database. :owner is the account id.
VISIBLE_PROJECTS = "(owner_id=:owner OR id IN (SELECT project_id FROM project_members WHERE user_id=:owner))"
