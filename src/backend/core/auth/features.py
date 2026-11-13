"""Governance of features (docs/PHASE2_PLAN.md R2, 12.3): who may use which part of the platform.

Each account role has default features, and an admin can allow or deny a feature for one member. The effective set is
resolved per request in `rules.access_problem`; every API route is either named here by feature or listed in CORE (a
test checks every route), so a new route is refused until someone decides. The environment admin has every feature.
Changes go to the hash-chained ledger of the hidden Platform project, with who, before and after.
"""
from __future__ import annotations

import json
import re

from backend.core.auth.base import ADMIN_ID, ROLES, AuthError, current_user, signer
from backend.db import db, now

PLATFORM_PROJECT = "prj_platform"  # hidden and archived, like the eval project: holds the governance ledger
FEATURES = {"harness": "Harness", "ba": "BA Studio", "qe": "QE cycle", "bugs": "Bugs and Feature", "skills": "Skill Studio",
            "mcp": "MCP", "docs": "Documents", "downloads": "Desktop downloads", "traces": "Traces", "usage": "Usage"}
DEFAULTS = {  # the plan's table (12.3); traces with the roles that run agents
    "qe_lead": ["harness", "ba", "qe", "bugs", "skills", "docs", "downloads", "traces"],
    "ba": ["ba", "docs"],
    "developer": ["harness", "qe", "bugs", "docs", "downloads", "traces"],
    "viewer": ["docs"],
}
# (path pattern, feature). BA Studio routes join with R3; usage is admin-only by its own rule as well.
ROUTES = [
    (re.compile(r"^/agui/harness$|^/api/harness(/|$)|^/api/chats/[^/]+/(todos|terminal)$"), "harness"),
    (re.compile(r"^/api/projects/[^/]+/sources(/|$)"), "ba"),
    (re.compile(r"^/api/(projects/[^/]+/)?findings(/|$)"), "bugs"),
    (re.compile(r"^/api/skill-studio(/|$)"), "skills"),
    (re.compile(r"^/api/mcp(/|$)"), "mcp"),
    (re.compile(r"^/api/(projects/[^/]+/)?(documents|templates)(/|$)"), "docs"),
    (re.compile(r"^/api/downloads(/|$)"), "downloads"),
    (re.compile(r"^/api/(traces|observability)(/|$)|^/api/projects/[^/]+/observability$"), "traces"),
    (re.compile(r"^/api/usage(/|$)"), "usage"),
]
# Everyone signed in (access still limited by role and project rules): sign-in, accounts, projects and their repository,
# gates, approvals, chat with the platform agents, and the admin's own areas.
# A run's feature is its workflow's (`WORKFLOWS`, checked when it starts); reading a run follows the project rules.
WORKFLOWS = {"ba": "ba", "brainstorm": "ba", "qe": "qe", "bug_scan": "bugs", "change": "bugs"}
CORE = re.compile(r"^/api/(health|auth|account|profile|features|users|settings|models|connections|logs|prompts|agents|evals|plugins|skills|capabilities|runs|"
                  r"approvals|chat|chats|memories|projects)(/|$)|^/agui/[^/]+$")


def feature_of(path: str) -> str | None:
    return next((feature for pattern, feature in ROUTES if pattern.match(path)), None)


def _load(key: str, default):
    with db() as con:
        found = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(found[0]) if found and found[0] else default


def role_defaults() -> dict[str, list[str]]:
    return {**DEFAULTS, **_load("feature_roles", {})}


def overrides() -> dict[str, dict[str, bool]]:
    """member id -> {feature: True (allow) | False (deny)}."""
    return _load("feature_overrides", {})


def effective(user: dict | None) -> list[str]:
    if not user:
        return []
    if user.get("role") == "admin" or user.get("id") == ADMIN_ID:
        return list(FEATURES)
    granted = set(role_defaults().get(user.get("account_role", ""), []))
    for feature, allowed in overrides().get(user["id"], {}).items():
        (granted.add if allowed else granted.discard)(feature)
    return [f for f in FEATURES if f in granted]


def allows(user: dict | None, feature: str) -> bool:
    return feature in effective(user)


def workflow_problem(user: dict | None, workflow: str) -> str:
    """Why this member may not start this workflow (R2), or "". An unknown name is left to the engine's own refusal; a test
    checks every registered workflow is listed in WORKFLOWS."""
    feature = WORKFLOWS.get(workflow)
    if not feature:
        return ""
    return "" if allows(user, feature) else f"Your access does not include {FEATURES[feature]}. Ask your administrator"


def _check(features) -> list[str]:
    if bad := [f for f in features if f not in FEATURES]:
        raise AuthError(f"Unknown feature {', '.join(bad)}. Features: {', '.join(FEATURES)}")
    return [f for f in FEATURES if f in features]


def _save(key: str, value, before, after, action: str, target: str) -> None:
    """Stores `value` under `key`; the ledger entry records `before` and `after` of what changed."""
    from backend.core import ledger

    with db() as con:
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived) VALUES (?,?,?,?,?,1)",
                    (PLATFORM_PROJECT, "Platform", "Platform governance ledger", now(), now()))
        con.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, json.dumps(value)))
    ledger.append(PLATFORM_PROJECT, signer(), action, target, {"before": before, "after": after})


def set_role_defaults(mapping: dict[str, list[str]]) -> dict[str, list[str]]:
    if bad := [r for r in mapping if r not in ROLES]:
        raise AuthError(f"Unknown role {', '.join(bad)}. Roles: {', '.join(ROLES)}")
    before = role_defaults()
    after = {**before, **{role: _check(features) for role, features in mapping.items()}}
    _save("feature_roles", after, before, after, "features.roles_changed", ",".join(sorted(mapping)))
    return role_defaults()


def set_override(user_id: str, feature: str, allowed: bool | None) -> dict[str, dict[str, bool]]:
    """allowed True or False sets an override for one member; None removes it (back to the role default)."""
    _check([feature])
    with db() as con:
        if not con.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            raise AuthError("No such member")
    before = overrides()
    after = json.loads(json.dumps(before))
    member = after.setdefault(user_id, {})
    if allowed is None:
        member.pop(feature, None)
    else:
        member[feature] = bool(allowed)
    if not member:
        after.pop(user_id)
    _save("feature_overrides", after, before.get(user_id, {}), after.get(user_id, {}), "features.override_changed", f"{user_id}:{feature}")
    return overrides()


def mine() -> dict:
    user = current_user.get()
    return {"features": effective(user), "names": FEATURES}
