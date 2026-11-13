"""Claude Code's Stop hook in MAF's harness loop (docs/PHASE2_PLAN.md section 9.3).

When the turn would end (the todo loop says done), the Stop hooks run with `stop_hook_active` and the last answer. A hook
that blocks (exit 2, `decision: block`) means "not finished yet": the loop goes on with its reason as the next message,
at most `LIMIT` times per turn so a hook can never keep the agent running forever. Hooks come from plugins and from the
managed and user settings files, through `core/plugin_hooks.dispatch`.
"""
from __future__ import annotations

import asyncio
import inspect
import re

from backend.core import plugin_hooks
from backend.maf.harness_kit import active_command

LIMIT = 3
# The agentic-qe skills tell Codex to ask for `approve create <path>` in chat and say Claude Code shows its own permission
# prompt instead. This harness is the Claude Code path: its approval card is that yes. A model that still asks in chat
# (deepseek, live QE cycle 2026-11-13) ends the turn with nothing written, so the loop goes on with the write.
CHAT_APPROVAL = re.compile(r"approve create|confirm the (file )?paths|explicit yes", re.I)
CHAT_APPROVAL_NEXT = ("Nothing was written: you asked for an approval in chat. Here the approval card on each write IS the user's explicit yes "
                      "(the plugin's Claude Code path), so never ask for `approve create`. Call file_access_write for each file the step "
                      "produces now; the user answers each card.")


async def _call(fn, **kwargs):
    result = fn(**kwargs)
    return await result if inspect.isawaitable(result) else result


def with_stop_hooks(ws, should_continue, next_message, limit: int = LIMIT, command: dict | None = None):
    """(should_continue, next_message) for `create_harness_agent`, wrapping the todo loop's pair."""
    state = {"count": 0, "reason": ""}

    async def check(**kwargs) -> bool:
        state["reason"] = ""
        if command and ws is not None and active_command.step_done(command, ws.root, ws.thread_id):
            return False  # the step's files are written and its check passes: open todos do not keep the turn going
        if await _call(should_continue, **kwargs):
            return True
        if ws is None or state["count"] >= limit:
            return False
        result = kwargs.get("last_result")
        text = str(getattr(result, "text", "") or "")[-4000:]
        if command and CHAT_APPROVAL.search(text[-1500:]):
            state["count"] += 1
            state["reason"] = CHAT_APPROVAL_NEXT
            return True
        outcome = await asyncio.to_thread(plugin_hooks.dispatch, "Stop", {"session_id": ws.thread_id, "stop_hook_active": state["count"] > 0,
                                                                          "last_assistant_message": text},
                                          project_id=ws.project_id, project_dir=ws.root, env_extra=ws.env())
        if not outcome.blocked:
            return False
        state["count"] += 1
        state["reason"] = outcome.reason
        return True

    async def message(**kwargs):
        if state["reason"] == CHAT_APPROVAL_NEXT:
            return CHAT_APPROVAL_NEXT
        if state["reason"]:
            return (f"A Stop hook says the work is not finished: {state['reason']}\nContinue until it is done, then stop. "
                    f"(Stop hook round {state['count']} of {limit}.)")
        return await _call(next_message, **kwargs)

    return check, message
