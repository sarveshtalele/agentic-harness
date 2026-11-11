"""Keep MAF's todo-loop nudges out of the user's reply.

Between iterations MAF's AgentLoopMiddleware injects user-role messages ("Progress so far: ...", "You still have N open
todo item(s)...") and also yields them in the stream. The AG-UI converter flattens every update into assistant text, so
without this the chat would show, and the store would keep, prompts the user never wrote. The loop middleware sits
outermost inside the agent, so this filter wraps the agent itself and drops only user-role updates.
"""
from __future__ import annotations

from typing import Any

from agent_framework import AgentResponse, AgentResponseUpdate, Content, ResponseStream


def _not_user(update: Any) -> list:
    """A nudge becomes a paragraph break, so each loop round's text reads as its own paragraph."""
    if str(getattr(update, "role", "") or "").lower() != "user":
        return [update]
    return [AgentResponseUpdate(role="assistant", contents=[Content.from_text("\n\n")], message_id=getattr(update, "message_id", None))]


class HideLoopNudges:
    """Delegates everything to the wrapped agent; a streamed run loses only its user-role updates."""

    def __init__(self, agent: Any):
        self._agent = agent

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)

    def run(self, *args: Any, **kwargs: Any) -> Any:
        result = self._agent.run(*args, **kwargs)
        if isinstance(result, ResponseStream):
            return result.flat_map(_not_user, AgentResponse.from_updates)
        return result


def while_working(should_continue: Any) -> Any:
    """Wrap MAF's loop predicate: an iteration that called no tool ends the loop. Without a tool call the model cannot
    complete a todo, so another round would only repeat its answer (and spend tokens) up to the round limit."""

    async def check(**loop_kwargs: Any) -> Any:
        result = loop_kwargs.get("last_result")
        called = any(getattr(content, "type", "") == "function_call"
                     for message in getattr(result, "messages", None) or [] for content in getattr(message, "contents", None) or [])
        if not called:
            return False
        verdict = should_continue(**loop_kwargs)
        return await verdict if hasattr(verdict, "__await__") else verdict

    return check
