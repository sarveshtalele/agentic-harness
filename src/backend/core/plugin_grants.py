"""Which roles may use a plugin (HS-12). No grant rows means open to every role, so existing installs keep working.
Once a plugin has a grant, only the granted roles and the admin may use its skills and commands. Mirrors core/mcp/grants.py.
"""
from __future__ import annotations

from collections.abc import Callable

from backend.core import ledger
from backend.core.auth import ROLES
from backend.db import db, new_id, now, row, rows


def role_of(user: dict | None) -> str | None:
    """The role grants check: admin, or the account role. None for a caller without a user (no filter)."""
    if not user:
        return None
    return "admin" if user.get("role") == "admin" else str(user.get("account_role") or "")


def _record(by: str, action: str, plugin_id: str, data: dict) -> None:
    """Plugins are platform-wide, so every project's ledger records the change, as agent settings do (maf/governance/policy.py)."""
    with db() as con:
        projects = [r[0] for r in con.execute("SELECT id FROM projects")]
    for project_id in projects:  # ponytail: one ledger per project; a platform ledger would be the upgrade
        ledger.append(project_id, by, action, plugin_id, data)


def listing(plugin_id: str) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT * FROM plugin_grants WHERE plugin_id=? ORDER BY granted_at", (plugin_id,)))


def add(plugin_id: str, role: str, by: str) -> dict:
    if role not in ROLES:
        raise ValueError(f"role is one of: {', '.join(ROLES)}")
    with db() as con:
        added = con.execute("INSERT OR IGNORE INTO plugin_grants (id, plugin_id, role, granted_by, granted_at) VALUES (?,?,?,?,?)",
                            (new_id("pgr"), plugin_id, role, by, now())).rowcount
        found = row(con.execute("SELECT * FROM plugin_grants WHERE plugin_id=? AND role=?", (plugin_id, role)))
    if added:  # granting a role twice changes nothing, so nothing is recorded
        _record(by, "plugin.grant_added", plugin_id, {"role": role, "grant_id": found["id"]})
    return found


def remove(plugin_id: str, grant_id: str, by: str) -> None:
    with db() as con:
        found = row(con.execute("SELECT * FROM plugin_grants WHERE id=? AND plugin_id=?", (grant_id, plugin_id)))
        if not found:
            raise KeyError(f"grant {grant_id}")
        con.execute("DELETE FROM plugin_grants WHERE id=?", (grant_id,))
    _record(by, "plugin.grant_removed", plugin_id, {"role": found["role"], "grant_id": grant_id})


def allowed(role: str | None) -> Callable[[str], bool]:
    """A check `plugin_id -> bool` for this role, reading the grants once. None or admin allows every plugin."""
    if role is None or role == "admin":
        return lambda _plugin_id: True
    with db() as con:
        given: dict[str, set] = {}
        for plugin_id, granted in con.execute("SELECT plugin_id, role FROM plugin_grants"):
            given.setdefault(plugin_id, set()).add(granted)
    return lambda plugin_id: plugin_id not in given or role in given[plugin_id]
