"""Agent construction: the tool audit middleware and the MAF Agent with its policy, prompt, skills and providers."""
from __future__ import annotations

import json
import time

from agent_framework import Agent, FunctionInvocationContext, SlidingWindowStrategy, function_middleware
from pydantic import BaseModel

from backend.config import MODEL_NO_CACHE
from backend.core import auth, prompts
from backend.core import skills as skill_lib
from backend.core.security import redact
from backend.maf import governance, llm, observability, skill_chat, tools
from backend.maf.runtime.context import ProjectContext
from backend.maf.runtime.emit import _emit

CHAT_AGENTS = {key: policy.name for key, policy in governance.POLICIES.items() if policy.chat_tools is not None}


def tool_audit(agent_key: str, project_id: str, run_id: str | None, source: str):
    """Every tool call is timed, filtered, shown on the run timeline, and stored for observability, redacted."""

    @function_middleware
    async def audit(context: FunctionInvocationContext, call_next) -> None:
        started = time.perf_counter()
        name = context.function.name
        args = context.arguments.model_dump() if isinstance(context.arguments, BaseModel) else dict(context.arguments)
        failure = ""
        try:
            await call_next()
            context.result = governance.guard_tool_result(agent_key, name, context.result, project_id, run_id)
        except Exception as exc:
            failure = str(exc) or type(exc).__name__
            raise
        finally:
            took = int((time.perf_counter() - started) * 1000)
            observability.record_tool(agent_key, project_id, run_id, source, name, args, took, failure)
            emit = _emit.get()
            if emit:
                emit("tool", f"{name} {redact(json.dumps(args, default=str))[:180]}", {"tool": name, "ms": took})

    return audit


def build(agent_key: str, project_id: str, tool_list=None, *, root=None, chat: bool = False, run_id: str | None = None, source: str = "workflow",
          user_id: str | None = None, model: str | None = None, choice: str = "", skill_set: skill_lib.Rendered | None = None) -> Agent:
    """`model` and `user_id` come from the caller when it already resolved them (AgentCall does). Chat passes `choice`, the thread's picked model.

    `skill_set` is the skill text the caller sends in its message. Its digest goes into the stored prompt reference and its names into `agent_calls.skills`.
    """
    governance.require_enabled(agent_key)
    user_id = user_id or auth.acting_user(project_id, run_id)
    if model is None:
        model = auth.model_for(project_id, agent_key, run_id, user_id, choice)
    auth.check_allowance(project_id, user_id, model)
    instructions = prompts.active(agent_key)["body"]
    # deny by default: a tool reaches the model only if this agent's policy lists it
    tool_list = governance.allowed(agent_key, tools.repo_tools(project_id, root) + list(tool_list or []), chat)
    options = {"max_tokens": governance.token_limit(agent_key)}
    if MODEL_NO_CACHE:  # LiteLLM's proxy cache would answer a retried prompt with the same bad reply
        options["extra_body"] = {"cache": {"no-cache": True}}
    ref = prompts.ref(agent_key) + (skill_lib.ref_suffix(skill_set) if skill_set else "")
    middleware = [tool_audit(agent_key, project_id, run_id, source), governance.telemetry(agent_key, project_id, run_id, source, model, user_id, ref, json.dumps(skill_set.items) if skill_set and skill_set.items else "")]
    providers = [ProjectContext(project_id, full=chat)]
    if chat and skill_set and skill_set.text:  # chosen by code for this turn (skill_chat.pick)
        providers.append(skill_chat.SkillText(skill_set.text))
    if chat and skill_chat.mode(agent_key, model) == "provider":  # this model passed the live tool check, so MAF loads skills itself
        providers.append(skill_chat.provider(agent_key))
    return Agent(
        client=llm.client(model), name=agent_key, instructions=instructions, tools=tool_list, context_providers=providers, middleware=middleware,
        compaction_strategy=SlidingWindowStrategy(keep_last_groups=30), default_options=options,
    )
