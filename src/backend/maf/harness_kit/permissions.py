"""Permission modes and rules for harness tools (docs/PHASE2_PLAN.md section 9.1 and 9.2), on MAF's tool approval.

Modes (per conversation, `/mode <name>`): `default` asks for every write, shell command and script; `acceptEdits` lets
file writes and edits inside the workspace through without a card; `plan` refuses writes and shell commands until the
person switches back; `auto` is `acceptEdits` until the OS sandbox exists (plan step 7), so shells still ask; `bypass`
allows everything, refused on the web profile.
Rules use Claude Code's syntax: `Bash(npm run *)`, `PowerShell(Get-ChildItem *)`, `Read(docs/**)`, `Edit(src/**)`,
`mcp__server__tool`, or a bare tool name; lists `allow`, `ask`, `deny`; deny wins, then ask, then allow. A shell rule
must hold for every part of a compound command (`a && b | c`). Sources: the user's `~/.aqh/settings.json` (not on web),
then the workspace's `.claude/settings.json`, `.claude/settings.local.json` and `.aqh/settings.json`. Repository files
are untrusted (CLAUDE.md), so their `deny` and `ask` rules apply but their `allow` rules are ignored until a folder
can be marked trusted (plan step 6). Decisions plug into MAF: `approval_rule` auto-approves allow and deny decisions so
no card shows, and `enforce` (function middleware) refuses the denied calls with the reason.
"""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

from agent_framework import FunctionInvocationContext, function_middleware
from pydantic import BaseModel

from backend import config

MODES = ("default", "acceptEdits", "plan", "auto", "bypass")
CLAUDE_NAME = {"bash": "Bash", "run_shell": "Bash", "powershell": "PowerShell", "file_access_write": "Write", "file_access_replace": "Edit",
               "file_access_replace_lines": "Edit", "file_access_delete": "Edit", "file_access_read": "Read", "file_access_read_lines": "Read",
               "read_file": "Read", "file_access_ls": "Read", "list_files": "Read", "file_access_grep": "Grep", "grep": "Grep",
               "run_skill_script": "Skill", "load_skill": "Skill"}
SHELLS = frozenset({"Bash", "PowerShell"})
EDITS = frozenset({"Write", "Edit"})
RULE = re.compile(r"^\s*([A-Za-z_][\w.-]*)\s*(?:\((.*)\))?\s*$")
SPLIT = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")


def mode_file(state_dir: Path, thread_id: str) -> Path:
    return state_dir / f"{thread_id}.mode"


def get_mode(state_dir: Path, thread_id: str) -> str:
    path = mode_file(state_dir, thread_id)
    mode = path.read_text(encoding="utf-8").strip() if path.is_file() else "default"
    return mode if mode in MODES and not (mode == "bypass" and config.PROFILE == "web") else "default"


def set_mode(state_dir: Path, thread_id: str, mode: str) -> str:
    """Set the conversation's mode; returns what the person reads."""
    match = next((m for m in MODES if m.lower() == mode.strip().lower()), None)
    if match is None:
        return f"Unknown mode {mode!r}. Modes: {', '.join(MODES)}."
    if match == "bypass" and config.PROFILE == "web":
        return "bypass is not allowed on the shared web server. Modes here: default, acceptEdits, plan, auto."
    state_dir.mkdir(parents=True, exist_ok=True)
    mode_file(state_dir, thread_id).write_text(match, encoding="utf-8")
    return f"Permission mode for this conversation: {match}."


def load_rules(root: Path | None) -> dict[str, list[str]]:
    rules = {"allow": [], "ask": [], "deny": []}
    sources: list[tuple[Path, bool]] = []
    if config.PROFILE != "web":
        sources.append((Path.home() / ".aqh" / "settings.json", True))
    if root is not None:
        sources += [(Path(root) / rel, False) for rel in (".claude/settings.json", ".claude/settings.local.json", ".aqh/settings.json")]
    for path, trusted in sources:
        try:
            block = json.loads(path.read_text(encoding="utf-8")).get("permissions", {}) if path.is_file() else {}
        except (OSError, ValueError, AttributeError):
            continue
        for kind in ("deny", "ask") + (("allow",) if trusted else ()):
            rules[kind] += [r for r in block.get(kind, []) if isinstance(r, str)]
    return rules


def _matches(rule: str, tool: str, args: dict, any_part: bool = False) -> bool:
    """Whether `rule` covers this call. Shell rules: every part of a compound command must match, or any part with `any_part`."""
    found = RULE.match(rule)
    if not found:
        return False
    name, spec = found[1], found[2]
    claude = CLAUDE_NAME.get(tool, tool)
    if name not in (claude, tool) and not (name.startswith("mcp__") and tool.startswith(name)):
        return name == "Edit" and claude == "Write" and _path_ok(spec, args)  # Edit rules cover Write, as in Claude Code
    if spec is None or spec in ("", "*"):
        return True
    if claude in SHELLS:
        pattern = spec[:-2] + " *" if spec.endswith(":*") else spec  # legacy `npm run:*`
        parts = [p for p in SPLIT.split(str(args.get("command", "")).strip()) if p]
        hits = [fnmatch.fnmatchcase(p, pattern) or p == pattern.removesuffix(" *") for p in parts]
        return bool(parts) and (any(hits) if any_part else all(hits))
    return _path_ok(spec, args)


def _path_ok(spec: str | None, args: dict) -> bool:
    path = str(args.get("file_name") or args.get("path") or args.get("directory") or "")
    if spec is None:
        return True
    pattern = spec.removeprefix("./")
    return fnmatch.fnmatch(path.removeprefix("./"), pattern) or fnmatch.fnmatch(path.removeprefix("./"), pattern.replace("**/", ""))


def decide(tool: str, args: dict, mode: str, rules: dict[str, list[str]]) -> tuple[str, str]:
    """("allow" | "ask" | "deny", reason)."""
    claude = CLAUDE_NAME.get(tool, tool)
    for rule in rules.get("deny", []):
        if _matches(rule, tool, args, any_part=True):
            return "deny", f"denied by the permission rule {rule}"
    if mode == "plan" and (claude in SHELLS | EDITS):
        return "deny", "plan mode: nothing is written or run until the plan is approved (switch with /mode default)"
    for rule in rules.get("ask", []):
        if _matches(rule, tool, args):
            return "ask", f"the rule {rule} asks"
    if mode == "bypass":
        return "allow", "bypass mode"
    if mode in ("acceptEdits", "auto") and claude in EDITS:
        return "allow", f"{mode} mode allows edits in the workspace"
    if claude in SHELLS:  # each part of a compound command needs an allow rule of its own
        parts = [p for p in SPLIT.split(str(args.get("command", "")).strip()) if p]
        covering = [next((r for r in rules.get("allow", []) if _matches(r, tool, {"command": part})), None) for part in parts]
        if parts and all(covering):
            return "allow", f"allowed by the permission rules {', '.join(sorted(set(covering)))}"
        return "ask", ""
    for rule in rules.get("allow", []):
        if _matches(rule, tool, args):
            return "allow", f"allowed by the permission rule {rule}"
    return "ask", ""


def approval_rule(mode_of, rules_of):
    """A MAF auto-approval callback: allow and deny pass without a card (deny is refused by `enforce`); ask shows one."""

    def rule(function_call) -> bool:
        verdict, _ = decide(function_call.name, dict(function_call.parse_arguments() or {}), mode_of(), rules_of())
        return verdict in ("allow", "deny")

    return rule


def enforce(mode_of, rules_of):
    @function_middleware
    async def permissions(context: FunctionInvocationContext, call_next) -> None:
        args = context.arguments.model_dump() if isinstance(context.arguments, BaseModel) else dict(context.arguments or {})
        verdict, reason = decide(context.function.name, args, mode_of(), rules_of())
        if verdict == "deny":
            context.result = f"Refused: {reason}. Nothing ran."
            return
        await call_next()

    return permissions
