"""Background commands for the harness shells (docs/PHASE2_PLAN.md section 5.2): servers, watchers and long jobs.

`bash(..., run_in_background=true)` starts the command as its own process (its own process group, so stopping it stops
its children), writes everything it prints to `.aqh/tasks/<id>.log` in the workspace, and returns at once. A task stops
by itself after 30 minutes (or the timeout the model gave, at most 2 hours), as in Claude Code. `task_output` reads a
task's log and status; `task_stop` ends it. Before each model turn, `BackgroundProvider` passes on what each task printed
since the model last looked and any task that ended, so the model can react to a log line or a finished build (Claude
Code's Monitor). Processes use `subprocess.Popen` and threads, not asyncio, so a task outlives the request that started it.
ponytail: tasks live in this server process; a restart stops them (their logs stay).
"""

import os
import secrets
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import psutil
from agent_framework import ContextProvider, tool
from pydantic import Field

from backend.core import ledger
from backend.core.security import redact

DEFAULT_S, MAX_S = 30 * 60, 2 * 60 * 60
UPDATE_CHARS = 2000


@dataclass
class Task:
    id: str
    kind: str
    command: str
    description: str
    log: Path
    proc: subprocess.Popen
    started: float
    limit_s: float
    seen: int = 0  # bytes of the log already passed to the model
    ended_reported: bool = False
    note: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)


_tasks: dict[str, dict[str, Task]] = {}


def start(ws, kind: str, program: str, command: str, description: str = "", timeout_ms: int | None = None) -> str:
    from backend.maf.harness_kit import shells

    folder = Path(ws.root) / ".aqh" / "tasks"
    folder.mkdir(parents=True, exist_ok=True)
    task_id = f"bg_{secrets.token_hex(3)}"
    log = folder / f"{task_id}.log"
    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    with log.open("wb") as out:
        proc = subprocess.Popen(shells.argv(kind, program, command), cwd=ws.root, env=shells.environment(ws), stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT, **group)
    limit = min(max((timeout_ms or DEFAULT_S * 1000) / 1000, 1), MAX_S)
    task = Task(task_id, kind, command, description, log, proc, time.monotonic(), limit)
    _tasks.setdefault(ws.thread_id, {})[task_id] = task
    threading.Thread(target=_watch, args=(task,), daemon=True).start()
    ledger.append(ws.project_id, "agent:harness", "harness.background.start", ws.thread_id,
                  {"task": task_id, "kind": kind, "command": redact(command)[:2000], "limit_s": limit, "user": ws.user_id})
    rel = log.relative_to(ws.root).as_posix()
    return (f"Started background task {task_id} ({description or command[:80]}). Its output goes to {rel}. "
            f"It stops by itself after {limit / 60:g} minutes. Read it with task_output(task_id='{task_id}'); stop it with task_stop. "
            "New output and its end are shown to you at the start of later turns.")


def _watch(task: Task) -> None:
    try:
        task.proc.wait(timeout=task.limit_s)
    except subprocess.TimeoutExpired:
        task.note = f"stopped after its {task.limit_s / 60:g}-minute limit"
        _kill(task.proc)


def _kill(proc: subprocess.Popen) -> None:
    """Stop a task and every process it started (terminate, then kill what is left after 3 s). Never raises."""
    if proc.poll() is not None:
        return
    try:
        root = psutil.Process(proc.pid)
        family = [root, *root.children(recursive=True)]
    except psutil.Error:
        return
    for p in family:
        try:
            p.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(family, timeout=3)
    for p in alive:
        try:
            p.kill()
        except psutil.Error:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def status(task: Task) -> str:
    code = task.proc.poll()
    if code is None:
        return f"running for {int(time.monotonic() - task.started)} s"
    return f"ended with exit code {code}" + (f" ({task.note})" if task.note else "")


def output(thread_id: str, task_id: str, tail_chars: int = 8000) -> str:
    task = _tasks.get(thread_id, {}).get(task_id)
    if task is None:
        return f"No background task {task_id} in this conversation. Known: {', '.join(_tasks.get(thread_id, {})) or 'none'}."
    text = redact(_plain(task.log.read_text(encoding="utf-8", errors="replace"))) if task.log.is_file() else ""
    with task.lock:
        task.seen = task.log.stat().st_size if task.log.is_file() else 0
    shown = text[-tail_chars:]
    cut = f"[{len(text) - len(shown)} earlier characters are in {task.log.name}]\n" if len(shown) < len(text) else ""
    return f"Task {task_id} ({task.description or task.command[:80]}): {status(task)}.\n{cut}{shown}".rstrip()


def stop(thread_id: str, task_id: str) -> str:
    task = _tasks.get(thread_id, {}).get(task_id)
    if task is None:
        return f"No background task {task_id} in this conversation."
    if task.proc.poll() is None:
        task.note = "stopped on request"
        _kill(task.proc)
    return f"Task {task_id}: {status(task)}."


def updates(thread_id: str) -> list[str]:
    """What each task printed since the model last looked, and tasks that ended; each reported once."""
    notes = []
    for task in _tasks.get(thread_id, {}).values():
        with task.lock:
            size = task.log.stat().st_size if task.log.is_file() else 0
            new = ""
            if size > task.seen:
                with task.log.open("rb") as f:
                    f.seek(task.seen)
                    new = redact(_plain(f.read().decode("utf-8", errors="replace")))
                task.seen = size
            ended = task.proc.poll() is not None and not task.ended_reported
            if ended:
                task.ended_reported = True
        if new or ended:
            head = f"Background task {task.id} ({task.description or task.command[:60]}): {status(task)}"
            body = f"\n{new[-UPDATE_CHARS:]}" if new else ""
            notes.append(head + body)
    return notes


def _plain(text: str) -> str:
    from backend.maf.harness_kit.shells import ANSI

    return ANSI.sub("", text)


def stop_all(thread_id: str) -> None:
    for task in _tasks.pop(thread_id, {}).values():
        _kill(task.proc)


def tools(ws) -> list:
    @tool(name="task_output", approval_mode="never_require",
          description="Read a background task's status and its latest output (from bash or powershell with run_in_background).")
    def task_output(task_id: Annotated[str, Field(description="The id the background start returned, like bg_1a2b3c.")],
                    tail_chars: Annotated[int, Field(description="How many of the last characters to show.", ge=200, le=30000)] = 8000) -> str:
        return output(ws.thread_id, task_id, tail_chars)

    @tool(name="task_stop", approval_mode="never_require", description="Stop a background task and every process it started.")
    def task_stop(task_id: Annotated[str, Field(description="The id the background start returned.")]) -> str:
        return stop(ws.thread_id, task_id)

    return [task_output, task_stop]


class BackgroundProvider(ContextProvider):
    """Before each run: background output and endings the model has not seen yet."""

    def __init__(self, thread_id: str):
        super().__init__("background_tasks")
        self.thread_id = thread_id

    async def before_run(self, *, agent, session, context, state) -> None:
        if notes := updates(self.thread_id):
            context.extend_instructions(self.source_id, "## Background tasks (new since your last turn)\n" + "\n\n".join(notes))
