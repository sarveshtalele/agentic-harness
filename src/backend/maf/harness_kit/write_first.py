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


READS = frozenset({"read_file", "list_files", "grep", "file_access_read", "file_access_read_lines", "file_access_ls", "file_access_grep", "read_skill_resource"})
WRITES = frozenset({"file_access_write", "file_access_replace", "file_access_replace_lines"})
NUDGE, LIMIT = 15, 25
_reads: dict[str, int] = defaultdict(int)  # ponytail: per process; a restart forgets the count, which only delays the nudge


def write_first(thread_id: str, root: Path | None, command: dict | None):
    """The middleware for one turn. `command` is the thread's active command, `root` its workspace."""

    @function_middleware
    async def guard(context: FunctionInvocationContext, call_next) -> None:
        name = context.function.name
        deferred = (command or {}).get("after_gate") is not None  # files that wait for a gate phrase must not be pushed out early
        missing = [] if deferred else [p for p in (command or {}).get("paths", []) if root is not None and not (root / p).is_file()]
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
                              "file_access_write from what you already know; you can extend it in later calls. Reads work again after a write.")
            return
        await call_next()
        if count >= NUDGE:
            context.result = f"{context.result}\n\n[harness] {count} reads in a row without a write. Write {todo} now with file_access_write; extend it later."

    return guard
