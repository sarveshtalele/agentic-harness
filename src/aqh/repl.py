"""Interactive `aqh` (docs/PHASE2_PLAN.md section 11.1): type a request, watch the answer stream, approve each card.

Local commands: /help, /exit, /clear (a new session), /resume (sessions of this folder), /doctor. Everything else,
including /mode, /rewind and plugin commands such as /agentic-qe:qe-start, goes to the harness as typed. Input history is
kept in ~/.aqh/history; Tab completes slash commands; Ctrl+C stops waiting for an answer, Ctrl+D or /exit leaves.
ponytail: a line-based terminal (prompt_toolkit input, rich output), not a full-screen app; `!` shell lines and
`Esc Esc` rewind come with the full-screen UI.
"""
from __future__ import annotations

import json
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console

from aqh import settings
from aqh.client import AqhError, Session

COMMANDS = ["/help", "/exit", "/clear", "/resume", "/doctor", "/mode", "/mode default", "/mode acceptEdits", "/mode plan", "/mode auto",
            "/mode bypass", "/rewind"]
HELP = ("Type a request. Local: /help /exit /clear (new session) /resume (pick a session) /doctor. Sent to the harness: "
        "/mode <default|acceptEdits|plan|auto|bypass>, /rewind [n], plugin commands like /agentic-qe:qe-start <app>.")


def _summary(args: str) -> str:
    try:
        data = json.loads(args or "{}")
    except ValueError:
        return args[:120]
    first = data.get("command") or data.get("file_name") or data.get("skill_name") or next(iter(data.values()), "") if data else ""
    return str(first).replace("\n", " ")[:120]


def run(session: Session, project_id: str, thread_id: str, folder: Path, console: Console | None = None, ask=None) -> None:
    console = console or Console()
    prompt = PromptSession(history=FileHistory(str(settings.home() / "history")), completer=WordCompleter(COMMANDS, sentence=True))
    ask = ask or (lambda question: console.input(question))
    console.print(f"[bold]aqh[/] in {folder}  (session {thread_id})  {HELP}", highlight=False)
    while True:
        try:
            line = prompt.prompt("› ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not line:
            continue
        if line in ("/exit", "/quit"):
            return
        if line == "/help":
            console.print(HELP, highlight=False)
            continue
        if line == "/clear":
            thread_id = session.new_thread(project_id)
            console.print(f"New session {thread_id}.")
            continue
        if line == "/resume":
            thread_id = _pick(session, project_id, console, ask) or thread_id
            continue
        if line == "/doctor":
            from aqh import doctor

            console.print(doctor.report(), highlight=False)
            continue
        try:
            printer = _printer(console)
            session.turn(thread_id, line, _decider(console, ask, printer.calls), printer, folder)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped waiting; the turn may still finish on the server.[/]")
        except AqhError as exc:
            console.print(f"[red]{exc}[/]")
        console.print()


def _pick(session: Session, project_id: str, console: Console, ask) -> str | None:
    threads = [t for t in session._ok(session.http.get(f"/api/projects/{project_id}/chats"), "Listing sessions") if t.get("agent") == "harness"][:10]
    for i, t in enumerate(threads, 1):
        console.print(f"{i}. {t['id']}  {t.get('title') or ''}  ({t.get('messages', 0)} messages, {t.get('updated_at', '')[:16]})", highlight=False)
    choice = ask("Session number (Enter to keep this one): ").strip()
    return threads[int(choice) - 1]["id"] if choice.isdigit() and 1 <= int(choice) <= len(threads) else None


def _printer(console: Console):
    calls: dict[str, dict] = {}

    def on_event(event: dict) -> None:
        kind = event.get("type")
        if kind == "TEXT_MESSAGE_CONTENT":
            console.print(event.get("delta", ""), end="", markup=False, highlight=False)
        elif kind == "TOOL_CALL_START":
            calls[event["toolCallId"]] = {"name": event.get("toolCallName", ""), "args": ""}
        elif kind == "TOOL_CALL_ARGS" and event.get("toolCallId") in calls:
            calls[event["toolCallId"]]["args"] += event.get("delta", "")
        elif kind == "TOOL_CALL_END" and event.get("toolCallId") in calls:
            call = calls[event["toolCallId"]]
            console.print(f"\n[cyan]● {call['name']}[/]([dim]{_summary(call['args'])}[/])", highlight=False)
        elif kind == "TOOL_CALL_RESULT":
            lines = str(event.get("content", "")).strip().splitlines()
            console.print("[dim]  ⎿ " + (lines[0][:160] if lines else "(no output)") + (f"  (+{len(lines) - 1} lines)" if len(lines) > 1 else "") + "[/]",
                          markup=True, highlight=False)
        elif kind == "RUN_ERROR":
            console.print(f"\n[red]{event.get('message')}[/]")

    on_event.calls = calls
    return on_event


def _decider(console: Console, ask, calls: dict):
    def decide(card: dict) -> bool:
        call = calls.get(card.get("toolCallId", ""), {})
        what = f"{call.get('name', '')}: {_summary(call.get('args', ''))}" if call else card.get("message", "this call")
        answer = ask(f"[yellow]Approve {what}?[/] [y/N] ").strip().lower()
        return answer in ("y", "yes")

    return decide
