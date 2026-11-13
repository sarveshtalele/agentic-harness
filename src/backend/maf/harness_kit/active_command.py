"""The thread's active plugin command (plan.md "Plugin command focus").

A typed `/plugin:command args` becomes the thread's active command. Its instructions go into the model's instructions on
every call through a MAF `ContextProvider`, so compaction can never summarise them away, and the chat history keeps only
what the user typed. While it is active the platform's own QE, document and repository tools are hidden, so the model
has one way to do each job: the workspace (MAF file access and the shell) under the plugin's hooks.

The command's "Paths this command may create" line is read from its own text, `<app-name>` filled in from the first
argument, and each path is shown as written or missing on disk, checked fresh before every model call.
"""
from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

from agent_framework import ContextProvider

from backend.core.security import safe_path
from backend.maf.harness_kit import hook_middleware, verify
from backend.maf.harness_kit.catalog import THREAD_ID

# The platform's own QE workflow, gates and documents. A plugin command does that work itself, with its own gates and files.
# The repository readers (list_files, read_file, grep) stay: they read the same commit as the workspace, and a model
# that reaches for them should not lose a round to "not found" (the 2026-11-11 live runs lost dozens that way).
PLATFORM_QE_TOOLS = frozenset({"start_workflow", "project_status", "run_tests", "list_findings", "verify_ledger",
                               "list_documents", "read_document", "search_documents", "save_document"})
HEAD = re.compile(r"^The user ran the command /(?P<name>[\w.-]+:[\w.-]+)(?P<args>[^\n]*?)\. Carry out")
BODY = re.compile(r"<command name=\"[^\"]+\">\n(?P<body>.*)\n</command>\s*$", re.S)
PATHS = re.compile(r"Paths this command may create:(?P<list>[^\n]*)")
CHECK = re.compile(r"`(node \"[^\"`]+/check-gate\.ts\" --gate \d+ --app <app-name>)`")


def _file(state_dir: Path, thread_id: str) -> Path:
    if not THREAD_ID.match(thread_id):
        raise ValueError("Unexpected thread id")
    return state_dir / f"{thread_id}.command.json"


def parse(expanded: str) -> dict | None:
    """The plugin command in `plugins.expand_slash` output, or None for anything else (a skill, plain text)."""
    head, body = HEAD.match(expanded or ""), BODY.search(expanded or "")
    if not head or not body:
        return None
    args = head["args"].strip()
    app = next((a for a in args.split() if not a.startswith("-")), "")
    found = PATHS.search(body["body"])
    # only the first sentence names what the command writes ("The plugin writes … never write those" follows it); an aside in
    # brackets is conditional (greenfield only); a wildcard or a folder is not one file that can be shown as written
    listed = re.sub(r"\([^)]*\)", "", found["list"].split(". ")[0]) if found else ""
    paths = [p.replace("<app-name>", app) for p in re.findall(r"`([^`]+)`", listed)
             if not p.startswith(".qe") and "*" not in p and not p.endswith("/") and (app or "<app-name>" not in p)]
    after = re.search(r"After the hook confirms Gate (\d+)", body["body"])  # qe-start: its files come only after the human's gate phrase
    check = CHECK.search(body["body"])  # the command's own done-check (agentic-qe: check-gate.ts), run after each write
    return {"name": head["name"], "args": args, "body": body["body"], "paths": paths, "after_gate": int(after[1]) if after else None,
            "check": shlex.split(check[1].replace("<app-name>", app)) if check and app else None}


def remember(state_dir: Path, thread_id: str, expanded: str | None) -> dict | None:
    """Make a typed plugin command the thread's active command. Other text leaves the active command as it is."""
    command = parse(expanded or "")
    if command:
        _file(state_dir, thread_id).write_text(json.dumps(command), encoding="utf-8")
    return command


def current(state_dir: Path, thread_id: str) -> dict | None:
    path = _file(state_dir, thread_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def file_state(root: Path | None, paths: list[str]) -> list[str]:
    if root is None:
        return [f"- {rel}: no workspace (this project has no repository)" for rel in paths]
    lines = []
    for rel in paths:
        try:
            target = safe_path(root, rel)
        except ValueError:
            lines.append(f"- {rel}: not a workspace path")
            continue
        size = target.stat().st_size if target.is_file() else 0
        lines.append(f"- {rel}: " + (f"written ({size} bytes)" if size else "MISSING"))
    return lines


def approved_gates(root: Path | None, app: str) -> list[int]:
    """Gates a person approved for this app, from the plugin's own ledger (`.qe/ledger.jsonl`, written by its hook)."""
    ledger = root / ".qe" / "ledger.jsonl" if root else None
    decisions: dict[int, str] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines() if ledger and ledger.is_file() else []:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("type") == "gate_decision" and r.get("source") == "user_prompt" and r.get("app") == app and isinstance(r.get("gate"), int):
            decisions[r["gate"]] = r.get("decision", "")
    return sorted(g for g, d in decisions.items() if d == "APPROVED")


class ActiveCommandContext(ContextProvider):
    """Puts the active plugin command and the state of its files into the instructions before every model call."""

    def __init__(self, command: dict, root: Path | None, thread_id: str = ""):
        super().__init__("harness-active-command")
        self.command, self.root, self.thread_id = command, root, thread_id

    async def before_run(self, *, agent, session, context, state) -> None:
        c = self.command
        files = file_state(self.root, c["paths"])
        checked = verify.last(self.thread_id) if c.get("check") else None
        blocked = hook_middleware.refused.get(self.thread_id, {})
        if checked:
            files.append(f"- the command's check, last run: {'PASS' if checked['passed'] else 'FAIL'}" + ("" if checked["passed"] else f" ({checked['output'][-300:]})"))
        app = next((a for a in c["args"].split() if not a.startswith("-")), "")
        gates = approved_gates(self.root, app)
        if c.get("after_gate") is not None:  # the model cannot see the plugin's hook record the gate phrase, so the ledger says it
            note = (f"Gate {c['after_gate']} is approved: write it now" if c["after_gate"] in gates
                    else f"written only after Gate {c['after_gate']} is approved; never before")
            files = [f"{line} ({note})" if line.endswith("MISSING") else line for line in files]
        context.extend_instructions(self.source_id, "\n".join([
            f"ACTIVE PLUGIN COMMAND: /{c['name']} {c['args']}".rstrip(),
            "You are carrying out this command until the user types another one. A message like \"continue\" or a gate phrase belongs to it.",
            "How to work here:",
            "- Do its steps in order, and only its steps: running the project's tests, installing packages or reading beyond what a step needs "
            "waits for the command that asks for it. The plugin's gates are the only gates.",
            "- The repository facts in your instructions (languages, frameworks, test runners, file counts) are already measured: use them, do not re-derive them.",
            "- Tools while it runs: file_access_ls, file_access_read, file_access_grep (read the workspace, no approval); describe_contract(path) "
            "(the fields a plugin file must have: call it before writing one) and check_gate(gate, app) (the plugin's own gate check); file_access_write, "
            "file_access_replace, file_access_replace_lines (change it, one approval card each); bash or powershell (run_shell on the web) for the plugin's scripts, tests and git; "
            "todos_*; load_skill and read_skill_resource (the plugin's skills); background_agents_* (the plugin's specialists). "
            f"These platform tools do not exist now, so never call them: {', '.join(sorted(PLATFORM_QE_TOOLS))}.",
            "- File tool paths are relative to the workspace root (for example `src/app.py` or `docs/qe/<app>/...`), never absolute. "
            "file_access_ls takes `directory`; file_access_read and file_access_write take `file_name`. An unknown argument is an error, not ignored.",
            "- Read only what the current step needs, and do not read a file twice.",
            "- Write each file the step produces with file_access_write as soon as you have enough evidence for it; extend it in later calls rather than holding everything back. "
            "Every write shows the user an approval card: that card IS the explicit yes the command asks for. This harness is the plugin's Claude Code path "
            "(\"Claude Code shows its own permission prompt instead\"): never list paths and wait, never ask for `approve create` in chat; make the write call.",
            "- Add one todo per file to write and per check to run, and complete each when it is done.",
            "- Never write a file the command says the plugin writes itself (gate reports, confidence, audit, coverage map, hand-off).",
            "- Run the command's check scripts with the shell tool (bash, powershell, or run_shell on the web). While a check prints FAIL, fix the files; ask for the gate phrase only when it passes.",
            f"- A plugin may open its write window only for its own command (agentic-qe: any other message closes it). If a hook blocks a write because "
            f"no phase command is running, do not retry the write: stop and ask the user to send `/{c['name']} {c['args']}`".rstrip() + "` again.",
            f"Gates a person approved for {app or 'this app'} (the plugin's ledger, read just now): {', '.join(map(str, gates)) or 'none yet'}.",
            "Files this command may create (checked on disk just now):", *(files or ["- none named"]),
            *([f"Files a plugin hook refused in this conversation (never write them): {', '.join(sorted(blocked))}"] if blocked else []),
            f"<command name=\"{c['name']}\">\n{c['body']}\n</command>"]))
