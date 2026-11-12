"""A time budget per harness turn instead of a small round cap (FINAL_PLAN 5.3, decision D2).

The leaderboard's strongest harnesses put no turn or step cap inside the harness; the old 25-round cap ended every
long turn with "reply continue". Rounds now have only a high safety limit (`ATLAS_HARNESS_MAX_ROUNDS`, default 200),
and each turn has a wall-clock budget (`ATLAS_HARNESS_TURN_MINUTES`, default 30). When it runs out, MAF's
`MiddlewareTermination` ends the tool loop cleanly and the user reads why and how to go on. Tokens are already
limited per person and model by the Usage page (`auth.check_allowance`).
"""
from __future__ import annotations

import time

from agent_framework import FunctionInvocationContext, MiddlewareTermination, function_middleware

from backend.config import HARNESS_TURN_MINUTES


stopped: dict[str, str] = {}  # thread -> notice; maf/agui.py shows it as the reply, since the stop ends the loop without model text


def turn_budget(thread_id: str = "", minutes: float | None = None):
    """The middleware for one turn; the clock starts when the turn's agent is built."""
    limit, started = 60 * (minutes if minutes is not None else HARNESS_TURN_MINUTES), time.monotonic()
    stopped.pop(thread_id, None)

    @function_middleware
    async def budget(context: FunctionInvocationContext, call_next) -> None:
        if time.monotonic() - started > limit:
            notice = f"Stopped: this turn used its {limit / 60:g}-minute budget, so its last tool call did not run. Reply \"continue\" to go on; the todos are kept."
            stopped[thread_id] = notice
            context.result = notice
            raise MiddlewareTermination(result=notice)
        await call_next()

    return budget
