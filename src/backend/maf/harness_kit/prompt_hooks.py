"""SessionStart and UserPromptSubmit hooks for the harness chat (plan H3), called by `maf/agui.py` for each new user message.

The hooks get the user's raw text (after redaction, before a slash command is expanded), so a typed phrase such as
`approve gate 0 for <app>` is recorded by the plugin's own approval hook in its own ledger, and `/agentic-qe:qe-start`
opens the plugin's write window. Only a human's message reaches these hooks: tool results and model text never do,
so no agent can approve a gate. The hooks' `additionalContext` is added to what the model reads for this turn; a block
ends the turn with the hook's reason, as in Claude Code. A project without a repository has no workspace, and no hook runs.
"""
from __future__ import annotations

import asyncio

from ag_ui.core import RunFinishedEvent, RunStartedEvent, TextMessageContentEvent, TextMessageEndEvent, TextMessageStartEvent

from backend.core import plugin_hooks
from backend.db import new_id
from backend.maf.harness_kit import workspace


async def submitted(project_id: str, thread_id: str, user_id: str | None, text: str, first: bool) -> plugin_hooks.Outcome:
    outcome = plugin_hooks.Outcome()
    try:
        ws = workspace.open_workspace(project_id, thread_id, user_id)
    except Exception as exc:  # a failed clone is reported to the model; it never fails the turn
        outcome.errors.append(f"the workspace could not be prepared, so no plugin hook ran: {type(exc).__name__}: {exc}")
        return outcome
    if ws is None:
        return outcome
    steps = ([("SessionStart", {"source": "startup"})] if first else []) + [("UserPromptSubmit", {"prompt": text})]
    for event, payload in steps:
        found = await asyncio.to_thread(plugin_hooks.dispatch, event, {"session_id": thread_id, **payload},
                                        project_id=project_id, project_dir=ws.root, env_extra=ws.env())
        outcome.context += found.context
        outcome.errors += found.errors
        outcome.ran += found.ran
        if found.blocked and event == "UserPromptSubmit":
            outcome.blocked, outcome.reason = True, found.reason
    return outcome


def for_model(text: str, outcome: plugin_hooks.Outcome) -> str:
    """The message the model reads: the text, then what the plugin hooks said about it."""
    notes = outcome.context + [f"Hook problem (reported, not fatal): {e}" for e in outcome.errors]
    return f"{text}\n\n<plugin-hook-context>\n" + "\n".join(notes) + "\n</plugin-hook-context>" if notes else text


def blocked_events(thread_id: str, run_id: str, reason: str) -> list:
    """A whole AG-UI run that only says the plugin blocked the message; the model is not called."""
    return reply_events(thread_id, run_id, f"A plugin hook blocked this message: {reason}")


def reply_events(thread_id: str, run_id: str, text: str) -> list:
    """A whole AG-UI run whose only content is `text` (no model call)."""
    message_id = new_id("msg")
    return [RunStartedEvent(thread_id=thread_id, run_id=run_id), TextMessageStartEvent(message_id=message_id, role="assistant"),
            TextMessageContentEvent(message_id=message_id, delta=text), TextMessageEndEvent(message_id=message_id),
            RunFinishedEvent(thread_id=thread_id, run_id=run_id)]
