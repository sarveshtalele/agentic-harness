"""Accounts and access. The admin login comes from .env. Users are created by the admin.

Passwords are salted scrypt hashes, usernames are encrypted at rest, and sessions are stored only as hashes.
Nothing here logs a username or password: audit records use the account's id.
"""
from __future__ import annotations

from backend.core.auth.allowance import _owner, acting_user, check_allowance, model_for, permit_model  # noqa: F401
from backend.core.auth.base import (ADMIN_ID, COOKIE, EVAL_PROJECT, IDLE_MINUTES, LOCK_SECONDS, MAX_FAILURES, ROLE_NAMES, ROLES, SESSION_HOURS,  # noqa: F401
                                    AuthError, Forbidden, _account, _admin_login, _event, _failures, _failures_lock, _inactive_reason, _lookup, _today, admin_configured, check_role, current_user, signer)
from backend.core.auth.passwords import _DUMMY_HASH, _verify_password, change_password, check_password_rules, hash_password  # noqa: F401
from backend.core.auth.projects import VISIBLE_PROJECTS, _id_for, _member_role, add_member, can_see_project, can_write, members, project_role, remove_member, transfer_project  # noqa: F401
from backend.core.auth.rules import ADMIN_ONLY, ADMIN_WRITES, OWNED_PATHS, OWNER_DELETE, OWNER_ONLY, SESSION_ONLY, VIEWER_MAY_WRITE, WRITES, access_problem, rule_of  # noqa: F401
from backend.core.auth.sessions import clock, login, logout, session_user  # noqa: F401
from backend.core.auth.signing import gate_roles, gate_signing_problem, require_gate_signer, set_gate_roles  # noqa: F401
from backend.core.auth.users import _check_dates, _public, create_user, describe, display_names, get_user, list_users, recent_events, tokens_used, update_user  # noqa: F401
from backend.core.errors import AllowanceError  # noqa: F401 - re-exported; callers use auth.AllowanceError
