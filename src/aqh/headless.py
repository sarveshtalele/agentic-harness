"""`aqh -p "prompt"`: one turn without a person at the keyboard (docs/PHASE2_PLAN.md section 11.1), for scripts and CI.

Output formats, as in Claude Code: `text` (the answer only), `json` (one result object at the end), `stream-json`
(every event as a JSON line, then the result). Nobody can answer an approval card here, so a card is approved only when
`--permission-mode bypass` is given or the call matches an `--allowedTools` rule (Claude Code syntax, `Bash(npm test)`);
anything else is refused and the answer says so. `--disallowedTools` refuses matching calls even then. Exit code 0 on
success, 1 when the turn failed or a call was refused.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from aqh.client import Session

PERMISSION_MODES = ("default", "acceptEdits", "plan", "auto", "bypass")


def _matches(rule: str, name: str, args: dict) -> bool:
    from backend.maf.harness_kit.permissions import _matches

    return _matches(rule, name, args)


def run(session: Session, project_id: str, thread_id: str, prompt: str, *, output: str = "text", mode: str | None = None,
        allowed: list[str] | None = None, disallowed: list[str] | None = None, folder: Path | None = None, out=sys.stdout) -> int:
    folder = folder or Path.cwd()
    calls: dict[str, dict] = {}
    text: list[str] = []
    refused: list[str] = []
    errors: list[str] = []
    started = time.time()

    def on_event(event: dict) -> None:
        kind = event.get("type")
        if kind == "TOOL_CALL_START":
            calls[event["toolCallId"]] = {"name": event.get("toolCallName", ""), "args": ""}
        elif kind == "TOOL_CALL_ARGS" and event.get("toolCallId") in calls:
            calls[event["toolCallId"]]["args"] += event.get("delta", "")
        elif kind == "TEXT_MESSAGE_CONTENT":
            text.append(event.get("delta", ""))
        elif kind == "RUN_ERROR":
            errors.append(str(event.get("message")))
        if output == "stream-json":
            out.write(json.dumps(event) + "\n")
            out.flush()

    def decide(card: dict) -> bool:
        call = calls.get(card.get("toolCallId", ""), {"name": "", "args": "{}"})
        try:
            args = json.loads(call["args"] or "{}")
        except ValueError:
            args = {}
        if any(_matches(rule, call["name"], args) for rule in disallowed or []):
            refused.append(call["name"])
            return False
        if mode == "bypass" or any(_matches(rule, call["name"], args) for rule in allowed or []):
            return True
        refused.append(call["name"])
        return False

    if mode:
        session.turn(thread_id, f"/mode {mode}", lambda _c: False, lambda _e: None, folder)
    session.turn(thread_id, prompt, decide, on_event, folder)
    answer = "".join(text).strip()
    if refused:
        answer += ("\n\n[aqh] Not approved (no one to ask in -p mode): " + ", ".join(dict.fromkeys(refused))
                   + ". Allow them with --allowedTools or --permission-mode.")
    result = {"type": "result", "subtype": "error" if errors else "success", "is_error": bool(errors or refused), "result": answer,
              "session_id": thread_id, "duration_ms": int((time.time() - started) * 1000), "errors": errors}
    if output == "text":
        out.write(answer + ("\n" + "\n".join(errors) if errors else "") + "\n")
    else:
        out.write(json.dumps(result) + "\n")
    out.flush()
    return 1 if errors or refused else 0
