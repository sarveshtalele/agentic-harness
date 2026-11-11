"""What a project's work may use: whose tokens, which model, and the limits."""
from __future__ import annotations

from backend.core import models
from backend.core.auth.base import ADMIN_ID, _account, _event, _inactive_reason, current_user
from backend.core.auth.users import tokens_used
from backend.core.errors import AllowanceError
from backend.db import db, row


def _owner(project_id: str) -> dict | None:
    with db() as con:
        found = con.execute("SELECT owner_id FROM projects WHERE id=?", (project_id,)).fetchone()
        if not found or not found[0] or found[0] == ADMIN_ID:
            return None
        return row(con.execute("SELECT * FROM users WHERE id=?", (found[0],)))


def acting_user(project_id: str, run_id: str | None = None) -> str | None:
    """Whose tokens a call spends: the account that started the run, else the signed-in account, else the project's owner."""
    if run_id:
        with db() as con:
            found = con.execute("SELECT user_id FROM runs WHERE id=?", (run_id,)).fetchone()
        if found and found[0]:
            return found[0]
    if user := current_user.get():
        return user["id"]
    owner = _owner(project_id)
    return owner["id"] if owner else None


def check_allowance(project_id: str, user_id: str | None = None, model: str = "") -> None:
    """Dates, the overall allocation, then the daily, weekly, monthly, and per-model limits, for the account that is spending."""
    account = _account(user_id or acting_user(project_id))
    if not account:
        return
    if reason := _inactive_reason(account):
        raise AllowanceError(f"{reason}. Ask your administrator")
    if account["token_limit"] is not None and tokens_used(account["id"]) >= account["token_limit"]:
        raise AllowanceError(f"This account has used its allocation of {account['token_limit']:,} tokens. Ask your administrator")
    if problem := models.limit_problem(account["id"], model):
        raise problem


def permit_model(user_id: str | None, name: str) -> str:
    """The one place a model is allowed or refused: the run form, chat, an agent's model, and the default all end here. A refusal is logged by account id."""
    account = _account(user_id)
    if account:
        allowed = models.allowed(account["id"])
        if not allowed:
            _event(account["id"], "model.refused:none")
            raise AllowanceError("No models are allowed for this account. Ask your administrator to tick at least one model for you")
        if name not in allowed:
            _event(account["id"], f"model.refused:{name}")
            raise AllowanceError(f"The model {name or '(none)'} is not allowed for this account. Choose one of: {', '.join(allowed)}. Or ask your administrator", model=name)
    elif models.is_disabled(name):
        raise AllowanceError(f"The model {name} is switched off in Settings")
    return name


def model_for(project_id: str, agent_key: str = "", run_id: str | None = None, user_id: str | None = None, choice: str = "") -> str:
    """Which model a call uses, first match wins: this run's or chat's choice, the agent's model, the user's default, the system default. Always checked."""
    user_id = user_id or acting_user(project_id, run_id)
    account = _account(user_id)
    if run_id and not choice:
        with db() as con:
            found = con.execute("SELECT model FROM runs WHERE id=?", (run_id,)).fetchone()
        choice = found[0] if found else ""
    from backend.maf import llm  # late: llm imports the database layer only, but this keeps core free of maf at import time

    name = choice or models.agent_model(agent_key) or (account["model"] if account else "") or models.system_default(llm.current()["model"])
    if not name and not account:
        return ""  # nothing configured: the client then says so
    return permit_model(user_id, name)
