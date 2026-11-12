"""Two loop-hygiene guards from the strongest harnesses (FINAL_PLAN 5.3), as one MAF function middleware.

- Repeat reminder (DeepSeek Harness `repeat-tool-reminder`): the same tool with the same arguments for the 3rd, 5th
  and 8th time in a turn gets a note asking the model to use the earlier result or change approach. Advisory only.
- Oversized results: a result over `LIMIT` characters keeps its head and tail and says how much was cut and how to
  read a range (Claude Code clears old tool output; DeepSeek Harness trims over 8,192 characters).
  ponytail: no spill files; a range read gets the rest. Spill to a file if ranges prove not enough.
"""
from __future__ import annotations

import json
from collections import Counter

from agent_framework import FunctionInvocationContext, function_middleware
from pydantic import BaseModel

from backend.maf.runtime.factory import _text

REMIND_AT = (3, 5, 8)
LIMIT, HEAD, TAIL = 12000, 8000, 2000


def tool_hygiene():
    """The middleware for one turn (its repeat counts start empty)."""
    seen: Counter = Counter()

    @function_middleware
    async def hygiene(context: FunctionInvocationContext, call_next) -> None:
        args = context.arguments.model_dump() if isinstance(context.arguments, BaseModel) else dict(context.arguments or {})
        key = (context.function.name, json.dumps(args, sort_keys=True, default=str))
        seen[key] += 1
        await call_next()
        text = _text(context.result)
        if len(text) > LIMIT:
            text = (f"{text[:HEAD]}\n\n[harness] {len(text) - HEAD - TAIL} characters cut from the middle of this {len(text)}-character result. "
                    f"Read a range (file_access_read_lines, or read_file with a line range) for the rest.\n\n{text[-TAIL:]}")
            context.result = text
        if seen[key] in REMIND_AT:
            context.result = (f"{text}\n\n[harness] This is call {seen[key]} of {context.function.name} with these same arguments in this turn. "
                              "Use the earlier result, change the approach, or finish.")

    return hygiene
