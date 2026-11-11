"""The agent registry joined with recorded calls, events, and evals."""
from __future__ import annotations

from dataclasses import asdict

from backend.core import prompts
from backend.db import db, rows
from backend.maf.agents import POLICIES
from backend.maf.governance.policy import settings, token_limit

def overview() -> list[dict]:
    """Registry joined with stored numbers. All figures come from recorded calls and events."""
    with db() as con:
        calls = {r["agent"]: r for r in rows(con.execute(
            """SELECT agent, COUNT(*) AS calls, SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out, CAST(AVG(latency_ms) AS INT) AS avg_latency_ms,
                      SUM(tool_calls) AS tool_calls, SUM(status='error') AS errors, MAX(created_at) AS last_call FROM agent_calls GROUP BY agent"""))}
        events = {r["agent"]: r["count"] for r in rows(con.execute("SELECT agent, COUNT(*) AS count FROM guardrail_events GROUP BY agent"))}
        latest_eval = {r["agent"]: r for r in rows(con.execute(
            "SELECT e.* FROM evaluations e JOIN (SELECT agent, MAX(created_at) AS at, MAX(rowid) AS id FROM evaluations GROUP BY agent) x ON e.rowid=x.id"))}
    result = []
    for key, policy in POLICIES.items():
        current = settings(key)
        stored = calls.get(key, {})
        evaluation = latest_eval.get(key)
        active = prompts.ref(key)
        result.append({
            "key": key, **{k: v for k, v in asdict(policy).items() if k not in {"workflow_tools", "chat_tools"}},
            "workflow_tools": sorted(policy.workflow_tools), "chat_tools": sorted(policy.chat_tools or []), "in_chat": policy.chat_tools is not None,
            "enabled": bool(current["enabled"]), "model": current.get("model", ""), "token_limit": token_limit(key), "settings_by": current["updated_by"], "settings_reason": current["reason"],
            "prompt_ref": active,
            "calls": stored.get("calls", 0), "tokens": (stored.get("tokens_in") or 0) + (stored.get("tokens_out") or 0), "avg_latency_ms": stored.get("avg_latency_ms"),
            "tool_calls": stored.get("tool_calls") or 0, "errors": stored.get("errors") or 0, "last_call": stored.get("last_call"), "guardrail_events": events.get(key, 0),
            "eval": {"passed": evaluation["passed"], "total": evaluation["total"], "prompt_ref": evaluation["prompt_ref"], "current": evaluation["prompt_ref"] == active, "created_at": evaluation["created_at"]} if evaluation else None,
        })
    return result


def recent_events(agent: str | None = None, limit: int = 50) -> list[dict]:
    query = "SELECT * FROM guardrail_events" + (" WHERE agent=?" if agent else "") + " ORDER BY id DESC LIMIT ?"
    with db() as con:
        return rows(con.execute(query, (agent, limit) if agent else (limit,)))
