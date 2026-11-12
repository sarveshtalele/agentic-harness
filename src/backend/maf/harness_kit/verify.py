"""Done means the command's own check passes, not that a file exists (FINAL_PLAN 5.3; live cycle 2026-11-11).

The model satisfied "write the file" with `"requirements": []`, and Gate 1 was refused three times. A plugin command
that names its check (agentic-qe: `node …/check-gate.ts --gate N --app <app>`) gets that check run after every
successful write, through the same sandbox runner as the shell (argument list, no shell, timeout, clean environment).
Its verdict and the tail of its output are appended to the write's result, so the model reads what is still missing,
and `write_first` keeps steering while it says FAIL. The last verdict per thread is kept for the instructions.
"""
from __future__ import annotations

import asyncio

from agent_framework import FunctionInvocationContext, function_middleware

from backend.core.security import redact
from backend.maf.runtime.factory import _text
from backend.repos import sandbox

WRITES = frozenset({"file_access_write", "file_access_replace", "file_access_replace_lines"})
TAIL = 1500
_last: dict[str, dict] = {}  # thread -> {"passed": bool, "output": str}; ponytail: per process, re-run after a restart


def last(thread_id: str) -> dict | None:
    return _last.get(thread_id)


async def run_check(ws, command: dict) -> dict | None:
    argv = (command or {}).get("check")
    if not argv or ws is None:
        return None
    out = await asyncio.to_thread(sandbox.execute_command, ws.project_id, argv, cwd=ws.root, timeout=120, extra_env=ws.env())
    text = redact(((out.get("stdout") or "") + "\n" + (out.get("stderr") or out.get("message") or "")).strip())
    result = {"passed": out.get("exit_code") == 0, "output": text[-TAIL:]}  # check-gate.ts exits 0 on PASS, 1 on FAIL
    _last[ws.thread_id] = result
    return result


def verifier(ws, command: dict | None):
    """The middleware for one turn: after a successful write, run the active command's check and report it."""

    @function_middleware
    async def verify(context: FunctionInvocationContext, call_next) -> None:
        await call_next()
        if context.function.name not in WRITES or not (command or {}).get("check") or _text(context.result).startswith(("Error", "Blocked", "Refused")):
            return
        verdict = await run_check(ws, command)
        if verdict:
            word = "PASS" if verdict["passed"] else "FAIL: fix what it lists, then write again"
            context.result = f"{_text(context.result)}\n\n[harness] the command's check ran after this write: {word}\n{verdict['output']}"

    return verify
