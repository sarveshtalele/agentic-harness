"""Per-agent settings, the admin kill switch, token limit, and tool policy."""
from __future__ import annotations

from backend.core import ledger, models
from backend.core.errors import AqeError
from backend.db import db, now, row, rows
from backend.maf.agents import POLICIES

class AgentDisabled(AqeError):  # not an AllowanceError: a disabled reviewer may be skipped, but an account that is out of tokens must stop the run
    code = "AQE-ALLOW-001"
    action = "Ask your administrator to enable the agent on the Agents page, then retry the stage."


def settings(agent: str) -> dict:
    with db() as con:
        found = row(con.execute("SELECT * FROM agent_settings WHERE agent=?", (agent,)))
    return found or {"agent": agent, "enabled": 1, "max_tokens": None, "model": "", "updated_by": "", "reason": "", "updated_at": None}


def update_settings(agent: str, enabled: bool, max_tokens: int | None, by: str, reason: str, model: str = "") -> dict:
    if agent not in POLICIES:
        raise KeyError(agent)
    if not by.strip():
        raise ValueError("A named person is required to change agent settings")
    if max_tokens is not None and not 500 <= max_tokens <= 64_000:
        raise ValueError("Token limit must be between 500 and 64000")
    model = model.strip()
    if model and not models.is_enabled(model):
        raise ValueError(f"{model} is not an enabled model. Add and enable it in Settings first")
    with db() as con:
        con.execute("INSERT OR REPLACE INTO agent_settings (agent, enabled, max_tokens, model, updated_by, reason, updated_at) VALUES (?,?,?,?,?,?,?)", (agent, int(enabled), max_tokens, model, by, reason, now()))
        projects = rows(con.execute("SELECT id FROM projects"))
    for project in projects:  # the agent is shared, so each project's audit trail records the change
        ledger.append(project["id"], by, "agent.settings", agent, {"enabled": enabled, "max_tokens": max_tokens, "model": model, "reason": reason})
    return settings(agent)


def require_enabled(agent: str) -> None:
    if not settings(agent)["enabled"]:
        reason = settings(agent)["reason"]
        raise AgentDisabled(f"Agent {POLICIES[agent].name} is disabled on the Agents page" + (f": {reason}" if reason else ""))


def token_limit(agent: str) -> int:
    return settings(agent)["max_tokens"] or POLICIES[agent].max_tokens


def allowed(agent: str, tool_list: list, chat: bool) -> list:
    """Deny by default: a tool reaches the model only if this agent's policy lists it."""
    policy = POLICIES[agent]
    permitted = (policy.chat_tools or frozenset()) if chat else policy.workflow_tools
    return [t for t in tool_list if t.name in permitted]
