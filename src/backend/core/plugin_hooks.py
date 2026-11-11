"""Claude Code hooks for the platform's plugins (plan H3): each enabled plugin's `hooks/hooks.json`, run the way Claude Code
runs them, so a plugin's own guards, ledger and approval-phrase hooks work inside the harness.

A hook command such as `node "${CLAUDE_PLUGIN_ROOT}/hooks/src/guard-bash.ts"` is split into an argument list first and the
variables are filled in per argument afterwards, so a path never becomes shell syntax. It runs with no shell, the hook JSON
on stdin, the hook's own timeout, `clean_env()` plus `CLAUDE_PLUGIN_ROOT` (the plugin folder) and `CLAUDE_PROJECT_DIR`
(the harness workspace). Blocks follow the Claude Code protocol: exit code 2 (reason on stderr), `"decision": "block"`, or
`hookSpecificOutput.permissionDecision: "deny"`. A hook that fails or times out never blocks and never crashes the turn: it
is reported in the outcome, logged redacted and written to the ledger like every other hook run.
"""
from __future__ import annotations

import json
import logging
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from backend.core import auth, ledger, plugin_grants, plugins
from backend.core.security import PathEscape, redact, safe_path
from backend.qe.execution.runners import clean_env

LOG = logging.getLogger("aqe.plugins.hooks")
DEFAULT_TIMEOUT = 60  # Claude Code's default when a hook names none
TAIL = 2000


@dataclass
class Outcome:
    blocked: bool = False
    reason: str = ""
    context: list[str] = field(default_factory=list)  # additionalContext from each hook, for the model
    errors: list[str] = field(default_factory=list)  # hooks that failed; reported, never fatal
    ran: list[dict] = field(default_factory=list)  # one row per hook run, as audited


def _hooks_json(plugin) -> dict:
    try:
        path = safe_path(plugin.root, "hooks/hooks.json")
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError, PathEscape) as exc:
        LOG.warning("plugin %s: hooks/hooks.json unreadable: %s", plugin.id, exc)
        return {}
    return data.get("hooks", {}) if isinstance(data, dict) and isinstance(data.get("hooks"), dict) else {}


def matching(event: str, tool_name: str = "") -> list[tuple]:
    """(plugin, hook) pairs for this event, in plugin order. A matcher is a regex on the Claude Code tool name; none matches all."""
    granted = plugin_grants.allowed(plugin_grants.role_of(auth.current_user.get()))
    found = []
    for plugin in plugins.discover():
        if plugin.id == "local-skills" or not plugin.enabled or not granted(plugin.id):
            continue
        for group in _hooks_json(plugin).get(event, []) or []:
            matcher = str(group.get("matcher") or "")
            if matcher and matcher != "*" and not re.fullmatch(matcher, tool_name or ""):
                continue
            found += [(plugin, hook) for hook in group.get("hooks", []) if hook.get("type") == "command" and hook.get("command")]
    return found


def argv_of(command: str, plugin_root: Path, project_dir: Path) -> list[str]:
    """`node "${CLAUDE_PLUGIN_ROOT}/x.ts"` -> [node path, <plugin>/x.ts]. Splitting comes before substitution."""
    values = {"CLAUDE_PLUGIN_ROOT": str(plugin_root), "CLAUDE_PROJECT_DIR": str(project_dir)}
    argv = [re.sub(r"\$\{(CLAUDE_PLUGIN_ROOT|CLAUDE_PROJECT_DIR)\}|\$(CLAUDE_PLUGIN_ROOT|CLAUDE_PROJECT_DIR)\b",
                   lambda m: values[m.group(1) or m.group(2)], part) for part in shlex.split(command)]
    if argv and (found := shutil.which(argv[0])):
        argv[0] = found
    return argv


def _parse(stdout: str) -> dict:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines or not lines[-1].lstrip().startswith("{"):
        return {}
    try:
        data = json.loads(lines[-1])  # hooks print one JSON object; anything before it is a plain message
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _run_one(plugin, hook: dict, payload: dict, project_dir: Path, env_extra: dict, outcome: Outcome) -> None:
    timeout = int(hook.get("timeout") or DEFAULT_TIMEOUT)
    argv = argv_of(str(hook["command"]), plugin.root, project_dir)
    env = clean_env({**env_extra, "CLAUDE_PLUGIN_ROOT": str(plugin.root), "CLAUDE_PROJECT_DIR": str(project_dir)})
    row = {"plugin": plugin.id, "event": payload.get("hook_event_name"), "tool": payload.get("tool_name", ""), "command": redact(str(hook["command"]))}
    try:
        proc = subprocess.run(argv, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout, cwd=project_dir, env=env, shell=False)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        error = f"{plugin.id} {row['event']} hook did not run: {type(exc).__name__}: {exc}"
        outcome.errors.append(redact(error))
        outcome.ran.append({**row, "exit_code": None, "error": redact(error)})
        return
    out = _parse(proc.stdout)
    specific = out.get("hookSpecificOutput") if isinstance(out.get("hookSpecificOutput"), dict) else {}
    reason = str(specific.get("permissionDecisionReason") or out.get("reason") or proc.stderr or "").strip()
    blocked = proc.returncode == 2 or out.get("decision") == "block" or specific.get("permissionDecision") == "deny" or out.get("continue") is False
    if blocked and not outcome.blocked:
        outcome.blocked, outcome.reason = True, reason or f"{plugin.id} hook blocked this"
    if text := str(specific.get("additionalContext") or "").strip():
        outcome.context.append(text)
    if proc.returncode not in (0, 2):
        outcome.errors.append(redact(f"{plugin.id} {row['event']} hook exited {proc.returncode}: {proc.stderr.strip()[-400:]}"))
    outcome.ran.append({**row, "exit_code": proc.returncode, "blocked": blocked, "decision": specific.get("permissionDecision") or out.get("decision") or "",
                        "reason": redact(reason)[-TAIL:], "stdout": redact(proc.stdout)[-TAIL:], "stderr": redact(proc.stderr)[-TAIL:]})


def dispatch(event: str, payload: dict, *, project_id: str, project_dir: Path, tool_name: str = "", env_extra: dict | None = None) -> Outcome:
    """Runs every matching hook in order (all of them, as Claude Code does) and audits each run in the project's ledger."""
    outcome = Outcome()
    hooks = matching(event, tool_name)
    body = {"hook_event_name": event, "cwd": str(project_dir), **payload}
    for plugin, hook in hooks:
        _run_one(plugin, hook, body, project_dir, env_extra or {}, outcome)
    for row in outcome.ran:
        ledger.append(project_id, f"plugin:{row['plugin']}", "plugin.hook", event, row)
        LOG.info("hook %s %s %s exit=%s blocked=%s %s", row["plugin"], event, row["tool"], row.get("exit_code"), row.get("blocked"), row.get("reason") or row.get("error") or "")
    for error in outcome.errors:
        LOG.warning("hook error: %s", error)
    return outcome
