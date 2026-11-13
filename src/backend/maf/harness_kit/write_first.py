"""Reading must turn into writing while a plugin command still owes its files (live cycle, 2026-11-11).

On personal-finance-mcp the model read 318 files across the qe-discover and qe-requirements turns and wrote none: every
turn ended at its round budget with "Let me explore the repository structure first", because context compaction
dropped what it had read, so it read it again. This MAF function middleware counts reads in a row per chat thread
while the active command has MISSING files:
- from `NUDGE` reads on, each read result ends with which file to write now;
- from `LIMIT` reads on, reads are refused until something is written.
A successful write resets the count. Without an active command, with all its files written, or for a command whose files
come only after a gate is approved (qe-start), nothing changes.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from agent_framework import FunctionInvocationContext, function_middleware

from backend.maf.harness_kit import active_command, verify


READS = frozenset({"read_file", "list_files", "grep", "file_access_read", "file_access_read_lines", "file_access_ls", "file_access_grep", "read_skill_resource"})
WRITES = frozenset({"file_access_write", "file_access_replace", "file_access_replace_lines"})
NUDGE, LIMIT = 15, 25
# the 2026-11-12 cycle wrote requirements citing 10 files that do not exist after being told to write "from what you know"
HONEST = ("with only what the files you have read support: cite only files you opened in this conversation and copy quotes "
          "verbatim from them; leave anything you have not read out for now.")
_reads: dict[str, int] = defaultdict(int)  # ponytail: per process; a restart forgets the count, which only delays the nudge


def write_first(thread_id: str, root: Path | None, command: dict | None):
    """The middleware for one turn. `command` is the thread's active command, `root` its workspace."""

    @function_middleware
    async def guard(context: FunctionInvocationContext, call_next) -> None:
        name = context.function.name
        gate = (command or {}).get("after_gate")  # files that wait for a gate phrase must not be pushed out early; once approved they are owed
        deferred = gate is not None and gate not in active_command.approved_gates(root, next((a for a in command["args"].split() if not a.startswith("-")), ""))
        missing = [] if deferred else [p for p in (command or {}).get("paths", []) if root is not None and not (root / p).is_file()]
        checked = verify.last(thread_id)
        if not deferred and not missing and checked and not checked["passed"]:  # written but not done: the command's check fails
            missing = [f"the fixes its check lists ({checked['output'][-200:]})"]
        if name in WRITES:
            await call_next()
            _reads[thread_id] = 0
            return
        if name not in READS or not missing:
            await call_next()
            return
        _reads[thread_id] += 1
        count, todo = _reads[thread_id], ", ".join(missing)
        if count > LIMIT:
            context.result = (f"Refused: {count - 1} reads in a row and nothing written while {todo} is missing. Write it now with "
                              f"file_access_write, {HONEST} Reads work again after a write, so you can extend it in later calls.")
            return
        await call_next()
        if count >= NUDGE:
            context.result = f"{context.result}\n\n[harness] {count} reads in a row without a write. Write {todo} now with file_access_write, {HONEST} Extend it later."

    return guard
