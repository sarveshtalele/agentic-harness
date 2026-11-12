"""Claude Code's Stop hook in MAF's harness loop (docs/PHASE2_PLAN.md section 9.3).

When the turn would end (the todo loop says done), the Stop hooks run with `stop_hook_active` and the last answer. A hook
that blocks (exit 2, `decision: block`) means "not finished yet": the loop goes on with its reason as the next message,
at most `LIMIT` times per turn so a hook can never keep the agent running forever. Hooks come from plugins and from the
managed and user settings files, through `core/plugin_hooks.dispatch`.
"""
from __future__ import annotations

import asyncio
import inspect

from backend.core import plugin_hooks

LIMIT = 3


async def _call(fn, **kwargs):
    result = fn(**kwargs)
    return await result if inspect.isawaitable(result) else result


def with_stop_hooks(ws, should_continue, next_message, limit: int = LIMIT):
    """(should_continue, next_message) for `create_harness_agent`, wrapping the todo loop's pair."""
    state = {"count": 0, "reason": ""}

    async def check(**kwargs) -> bool:
        state["reason"] = ""
        if await _call(should_continue, **kwargs):
            return True
        if ws is None or state["count"] >= limit:
            return False
        result = kwargs.get("last_result")
        text = str(getattr(result, "text", "") or "")[-4000:]
        outcome = await asyncio.to_thread(plugin_hooks.dispatch, "Stop", {"session_id": ws.thread_id, "stop_hook_active": state["count"] > 0,
                                                                          "last_assistant_message": text},
                                          project_id=ws.project_id, project_dir=ws.root, env_extra=ws.env())
        if not outcome.blocked:
            return False
        state["count"] += 1
        state["reason"] = outcome.reason
        return True

    async def message(**kwargs):
        if state["reason"]:
            return (f"A Stop hook says the work is not finished: {state['reason']}\nContinue until it is done, then stop. "
                    f"(Stop hook round {state['count']} of {limit}.)")
        return await _call(next_message, **kwargs)

    return check, message
