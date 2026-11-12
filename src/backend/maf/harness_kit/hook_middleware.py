"""Plugin hooks and sandbox slots around the harness's write and shell tools (plan H2 and H3), as MAF function middleware.

MAF runs function middleware after the human approved the call, right before the tool body. For a write or shell call
this middleware takes a sandbox slot (web profile, `leases.py`), runs the plugins' PreToolUse hooks with the Claude Code
tool name their matchers expect (`Write`, `Edit`, `Bash`) and Claude Code's `tool_input` shape, and only then the tool.
A block (exit code 2, `decision: block`, or `permissionDecision: deny`) skips the tool and returns the hook's reason as the
tool result, so the model reads why. `ask` counts as allowed, because the human already approved this exact call. After
the tool, PostToolUse hooks run with its result; their `additionalContext` is appended to the result.
"""
from __future__ import annotations

import asyncio
import shlex

from agent_framework import FunctionInvocationContext, function_middleware
from pydantic import BaseModel

from backend.core import plugin_hooks
from backend.maf.harness_kit import leases
from backend.maf.harness_kit.shell import NAME as SHELL
from backend.maf.runtime.factory import _text

WRITES = {"file_access_write": "Write", "file_access_replace": "Edit", "file_access_replace_lines": "Edit", "file_access_delete": "Bash"}
# thread -> {file: hook reason}. A file a hook refused stays refused for the thread: the live cycle retried plugin-owned
# files 14 times across turns, each with an approval card. ponytail: per process; a restart lets one retry through.
refused: dict[str, dict[str, str]] = {}


SHELL_NAMES = {SHELL: "Bash", "bash": "Bash", "powershell": "PowerShell"}  # hooks that inspect shells match Bash|PowerShell


def claude_call(name: str, args: dict, root) -> tuple[str, dict]:
    """The Claude Code tool name and tool_input for one harness call. A delete is shown to hooks as the `rm` it is."""
    if name in SHELL_NAMES:
        return SHELL_NAMES[name], {"command": str(args.get("command", "")), "description": str(args.get("description", ""))}
    path = str(root / str(args.get("file_name", "")))
    if name == "file_access_write":
        return "Write", {"file_path": path, "content": str(args.get("content", ""))}
    if name == "file_access_replace":
        return "Edit", {"file_path": path, "old_string": str(args.get("old_string", "")), "new_string": str(args.get("new_string", ""))}
    if name == "file_access_replace_lines":
        lines = [str((e.get("new_line") if isinstance(e, dict) else getattr(e, "new_line", "")) or "") for e in args.get("edits") or []]
        return "Edit", {"file_path": path, "old_string": "", "new_string": "".join(lines)}
    return "Bash", {"command": f"rm {shlex.quote(path)}"}


def _args(context) -> dict:
    return context.arguments.model_dump() if isinstance(context.arguments, BaseModel) else dict(context.arguments or {})


CLAUDE_KEYS = {"command": "command", "file_path": "file_name", "content": "content", "old_string": "old_string", "new_string": "new_string"}


def _apply(context, name: str, updated: dict) -> None:
    """Merge a hook's updatedInput (Claude Code's field names) into this call's arguments."""
    mapped = {CLAUDE_KEYS.get(k, k): v for k, v in updated.items() if CLAUDE_KEYS.get(k, k) in _args(context)}
    if name in WRITES and "file_name" in mapped:
        mapped.pop("file_name")  # a hook may not redirect a write to another path
    if isinstance(context.arguments, BaseModel):
        context.arguments = context.arguments.model_copy(update=mapped)
    else:
        context.arguments = {**dict(context.arguments or {}), **mapped}


def guarded(workspace):
    """The middleware for one harness turn; `workspace` is the thread's workspace (hooks get it as CLAUDE_PROJECT_DIR)."""

    async def hooks(event: str, tool: str, payload: dict) -> plugin_hooks.Outcome:
        return await asyncio.to_thread(plugin_hooks.dispatch, event, {"session_id": workspace.thread_id, "tool_name": tool, **payload},
                                       project_id=workspace.project_id, project_dir=workspace.root, tool_name=tool, env_extra=workspace.env())

    @function_middleware
    async def guard(context: FunctionInvocationContext, call_next) -> None:
        name = context.function.name
        if name not in SHELL_NAMES and name not in WRITES:
            await call_next()
            return
        args = _args(context)
        tool, tool_input = claude_call(name, args, workspace.root)
        target = str(args.get("file_name", "")) if name in WRITES else ""
        earlier = refused.get(workspace.thread_id, {}).get(target) if target else None
        if earlier:
            context.result = (f"Refused without running: a plugin hook already blocked writing {target} in this conversation, and it will "
                              f"block it again. Do not write this file. The hook said: {earlier}")
            return
        try:
            with leases.lease("shell" if name in SHELL_NAMES else "write", workspace.project_id, workspace.thread_id, workspace.user_id):
                before = await hooks("PreToolUse", tool, {"tool_input": tool_input})
                if before.blocked:
                    if target:
                        refused.setdefault(workspace.thread_id, {})[target] = before.reason
                    context.result = f"Blocked by a plugin hook before {name} ran. Nothing ran. Reason: {before.reason}"
                    return
                if before.updated_input:  # Claude Code's updatedInput: a hook rewrote the call, e.g. added a flag
                    _apply(context, name, before.updated_input)
                    tool, tool_input = claude_call(name, _args(context), workspace.root)
                try:
                    await call_next()
                except Exception as exc:
                    await hooks("PostToolUseFailure", tool, {"tool_input": tool_input, "error": str(exc)[:4000]})
                    raise
                failed = _text(context.result).lstrip().startswith(("Error", "Refused"))
                after = await hooks("PostToolUseFailure" if failed else "PostToolUse", tool,
                                    {"tool_input": tool_input, **({"error": _text(context.result)[:4000]} if failed else
                                                                  {"tool_response": {"result": _text(context.result)[:20000]}})})
        except leases.SandboxBusy as exc:
            context.result = exc.message
            return
        notes = before.context + after.context + [f"Hook problem (reported, not fatal): {e}" for e in before.errors + after.errors]
        if after.blocked:
            notes.append(f"A plugin hook flagged this result: {after.reason}")
        if notes:
            context.result = f"{_text(context.result)}\n\n" + "\n".join(notes)

    return guard
