"""The route ownership rules: deny by default, admin-only, owned, and session-only paths."""
from __future__ import annotations

import re

from backend.core.auth.projects import project_role
from backend.db import db

OWNED_PATHS = [
    (re.compile(r"^/api/projects/([^/]+)"), "SELECT id AS project_id FROM projects WHERE id=?"),
    (re.compile(r"^/api/documents/([^/]+)"), "SELECT project_id FROM documents WHERE id=?"),
    (re.compile(r"^/api/runs/([^/]+)"), "SELECT project_id FROM runs WHERE id=?"),
    (re.compile(r"^/api/findings/([^/]+)"), "SELECT project_id FROM findings WHERE id=?"),
    (re.compile(r"^/api/approvals/([^/]+)"), "SELECT project_id FROM approvals WHERE id=?"),
    (re.compile(r"^/api/chats/([^/]+)"), "SELECT project_id FROM chat_threads WHERE id=?"),
    (re.compile(r"^/api/memories/([^/]+)"), "SELECT project_id FROM memories WHERE id=?"),
]
ADMIN_ONLY = re.compile(r"^/api/(users|connections|logs|auth/events|models|usage|capabilities/sync)(/|$)|^/api/agents/guardrail-events$|^/api/projects/[^/]+/(repo/local|transfer|workspace)$")
ADMIN_WRITES = re.compile(r"^/api/(settings|prompts|agents|evals|skills/[^/]+/health)(/|$)")
OWNER_ONLY = re.compile(r"^/api/projects/[^/]+/members(/|$)")  # also the admin
OWNER_DELETE = re.compile(r"^/api/projects/[^/]+$")
# /api/traces is session-only here; core/tracing/queries.py limits each answer to the caller's own runs (404 otherwise).
# Signed-in users with no project in the path. A path in none of these lists is refused, so a new route has to be added here or above.
SESSION_ONLY = re.compile(r"^(/agui/[^/]+|/api/(auth/(me|logout|desktop-session)|account/(password|email)|chat/agents|profile|approvals|documents|findings|projects|harness(/.*)?|observability(/errors|/export)?|plugins(/.*)?|templates(/upload|/[^/]+)?"
                          r"|prompts(/[^/]+(/scores)?)?|skills(/.*)?|skill-studio(/.*)?|agents(/[^/]+(/metrics)?)?|evals(/[^/]+)?|mcp(/.*)?|settings/(llm|models|timezone|gate-roles)|traces(/[^/]+)?|capabilities(/.*)?))$")
VIEWER_MAY_WRITE = re.compile(r"^/api/(auth/(logout|desktop-session)|account/(password|email))$")  # a viewer can still sign out and change their own password
WRITES = {"POST", "PUT", "PATCH", "DELETE"}


def rule_of(path: str) -> str | None:
    """Which rule covers a path: admin, owned, session, or None when no rule does."""
    if ADMIN_ONLY.search(path):
        return "admin"
    if any(p.match(path) for p, _ in OWNED_PATHS):
        return "owned"
    if ADMIN_WRITES.search(path) or SESSION_ONLY.match(path):
        return "session"
    return None


def access_problem(method: str, path: str, user: dict) -> tuple[int, str] | None:
    """Returns the status and message to refuse with. Someone else's item answers 404, so its existence is not revealed."""
    if user["role"] == "admin":
        return None
    write = method in WRITES
    if ADMIN_ONLY.search(path) or (write and ADMIN_WRITES.search(path)):
        return 403, "Only an administrator can do this"
    if write and user["account_role"] == "viewer" and not VIEWER_MAY_WRITE.match(path):
        return 403, "Your role is viewer. A viewer can read but not start, change, or approve anything"
    for pattern, query in OWNED_PATHS:
        if match := pattern.match(path):
            with db() as con:
                found = con.execute(query, (match.group(1),)).fetchone()
            role = project_role(found[0], user) if found else None
            if not role:
                return 404, "Not found"
            if (OWNER_ONLY.match(path) or (method == "DELETE" and OWNER_DELETE.match(path))) and role != "owner":
                return 403, "Only the project owner or an administrator can do this"
            if write and role == "viewer":
                return 403, "Your role in this project is viewer. A viewer can read but not start, change, or approve anything"
            return None
    return None if rule_of(path) else (403, "This path has no access rule")
