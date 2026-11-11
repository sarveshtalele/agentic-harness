"""Call telemetry: MAF chat middleware that checks the allowance and records every model round."""
from __future__ import annotations

import time

from agent_framework import chat_middleware

from backend.core import auth, prompts
from backend.core.security import redact
from backend.db import db, now, rows
from backend.maf import observability
from backend.maf.agents import POLICIES

SKILL_TOOLS = {"load_skill", "read_skill_resource"}  # MAF SkillsProvider tools, offered only on a model that passed the tool check


def record_call(agent: str, project_id: str | None, run_id: str | None, source: str, usage: dict, latency_ms: int, tool_calls: int, status: str, error: str = "", model: str = "", user_id: str | None = None,
                prompt_ref: str = "", skills: str = "") -> None:
    """`prompt_ref` names the prompt and the skill text actually sent; `skills` is the JSON list of skills used (see core/skills.py)."""
    with db() as con:
        con.execute(
            "INSERT INTO agent_calls (agent, project_id, run_id, source, prompt_ref, tokens_in, tokens_out, latency_ms, tool_calls, status, error, created_at, model, user_id, skills) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (agent, project_id, run_id, source, prompt_ref or prompts.ref(agent), usage.get("input_token_count") or 0, usage.get("output_token_count") or 0, latency_ms, tool_calls, status, redact(error)[:400], now(), model, user_id, skills),
        )


def telemetry(agent: str, project_id: str | None, run_id: str | None, source: str, model: str = "", user_id: str | None = None, prompt_ref: str = "", skills: str = "",
              also_allowed: frozenset = frozenset()):
    """MAF chat middleware: stops a round when a limit is reached, and records each model round, streamed or not, with the model and account."""

    @chat_middleware
    async def record(context, call_next) -> None:
        auth.check_allowance(project_id or "", user_id, model)  # a tool loop makes many rounds, so the limit is checked before each one
        started = time.perf_counter()
        try:
            await call_next()
        except Exception as exc:
            record_call(agent, project_id, run_id, source, {}, int((time.perf_counter() - started) * 1000), 0, "error", str(exc), model, user_id, prompt_ref, skills)
            raise
        if context.stream:
            def finished(response):
                _record_refused_tools(agent, project_id, run_id, source, response, also_allowed)
                record_call(agent, project_id, run_id, source, dict(response.usage_details or {}), int((time.perf_counter() - started) * 1000), _tool_count(response), "ok", "", model, user_id, prompt_ref, skills)
                return response

            # A hook on the stream itself runs for plain agents and inside MAF's harness alike; the harness does not
            # apply `context.stream_result_transforms`, so streamed harness calls went unrecorded (found in the P2 live run).
            context.result.with_result_hook(finished)
            return
        response = context.result
        _record_refused_tools(agent, project_id, run_id, source, response, also_allowed)
        record_call(agent, project_id, run_id, source, dict(response.usage_details or {}), int((time.perf_counter() - started) * 1000), _tool_count(response), "ok", "", model, user_id, prompt_ref, skills)

    return record


def _record_refused_tools(agent: str, project_id: str | None, run_id: str | None, source: str, response, also_allowed: frozenset = frozenset()) -> None:
    """A tool the agent may not use never reaches the tool middleware, so its request is logged here for the audit trail."""
    policy = POLICIES[agent]
    allowed = (policy.chat_tools or frozenset()) if source == "chat" else policy.workflow_tools
    allowed = allowed | also_allowed  # e.g. the MCP tools granted to this user in the harness
    for message in response.messages:
        for content in message.contents:
            if content.type == "function_call" and content.name not in allowed and content.name not in SKILL_TOOLS:
                observability.record_tool(agent, project_id, run_id, source, content.name, {"requested": str(content.arguments)[:2000]}, 0, "Refused: not allowed for this agent")


def _tool_count(response) -> int:
    return sum(1 for m in response.messages for c in m.contents if c.type == "function_call")


def recent_calls(agent: str, limit: int = 30) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT * FROM agent_calls WHERE agent=? ORDER BY id DESC LIMIT ?", (agent, limit)))
