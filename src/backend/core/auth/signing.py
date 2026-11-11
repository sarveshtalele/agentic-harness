"""Which roles may sign each gate."""
from __future__ import annotations

import json

from backend.core.auth.base import ROLE_NAMES, ROLES, AuthError, Forbidden, _event, current_user, signer
from backend.core.auth.projects import _member_role, can_write, project_role
from backend.db import db


def gate_roles() -> dict[int, list[str]]:
    """Gate number to the roles that may sign it. A gate with no entry may be signed by any role that can write."""
    with db() as con:
        found = con.execute("SELECT value FROM settings WHERE key='gate_roles'").fetchone()
    stored = json.loads(found[0]) if found and found[0] else {}
    return {int(g): list(r) for g, r in stored.items() if r}


def set_gate_roles(mapping: dict) -> dict[int, list[str]]:
    clean = {}
    for gate, names in mapping.items():
        if str(gate) not in {str(n) for n in range(6)}:
            raise AuthError(f"Unknown gate {gate}. Gates are 0 to 5")
        if bad := [n for n in names if n not in ROLES or n == "viewer"]:
            raise AuthError(f"{', '.join(bad)} cannot sign a gate. Use: {', '.join(r for r in ROLES if r != 'viewer')}")
        if names:
            clean[str(int(gate))] = list(dict.fromkeys(names))
    with db() as con:
        con.execute("INSERT OR REPLACE INTO settings VALUES ('gate_roles', ?)", (json.dumps(clean),))
    _event(signer(), "gate_roles.changed")
    return gate_roles()


def gate_signing_problem(project_id: str, gate: int, user: dict | None = None) -> str:
    """Empty when the signed-in account may sign this gate; otherwise the refusal, naming the roles needed. The admin may always sign."""
    user = user or current_user.get()
    role = project_role(project_id, user)
    if role == "admin":
        return ""
    if not can_write(project_id, user):
        return "Your role cannot approve here. A viewer can read but never sign"
    needed = gate_roles().get(gate)
    if not needed:
        return ""
    held = [user["account_role"]] + ([_member_role(project_id, user["id"])] if role not in {"owner", "admin"} else [])
    if all(r in needed for r in held):
        return ""
    return f"Gate G{gate} can be signed only by: {', '.join(ROLE_NAMES[r] for r in needed)}. You hold: {', '.join(ROLE_NAMES[r] for r in dict.fromkeys(held))}"


def require_gate_signer(project_id: str, gate: int) -> None:
    if problem := gate_signing_problem(project_id, gate):
        raise Forbidden(problem)
