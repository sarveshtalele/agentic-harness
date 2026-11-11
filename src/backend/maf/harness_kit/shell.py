"""The harness shell (plan H2, decisions D8 and D9) on MAF's own shell tooling (`agent-framework-tools`).

`WorkspaceShell` is MAF's `LocalShellTool` (its `as_function()` tool, approval mode `always_require`, so every command gets
an approval card) with `run` replaced: MAF's runner hands the text to bash or PowerShell, and CLAUDE.md allows no shell.
Here the text is split into an argument list, checked against the allowlist, and run by `repos.sandbox.execute_command`
(no shell, `clean_sandbox_env()`, timeout `ATLAS_HARNESS_SHELL_TIMEOUT`) with the workspace as the working directory.
Every command that runs goes to the project ledger with its exit code and the tail of its output, redacted.
ponytail: allowlisted programs (node, python) can still read and write outside the workspace once a human approves the
command; the folder and environment isolate, the operating system does not. A container per job closes that.
"""
from __future__ import annotations

import asyncio
import shlex
import time

from agent_framework import Content
from agent_framework_tools.shell import LocalShellTool, ShellCommandError, ShellEnvironmentProvider, ShellEnvironmentProviderOptions, ShellResult

from backend.config import HARNESS_SHELL_TIMEOUT
from backend.core import ledger
from backend.core.security import redact
from backend.repos import sandbox

PROGRAMS = frozenset({"node", "npx", "npm", "python", "python3", "pytest", "git"})
GIT_READ = frozenset({"status", "log", "diff", "show", "ls-files", "rev-parse", "branch"})
GIT_REFUSED_FLAGS = ("--output", "--ext-diff", "--no-index", "--textconv")  # these write files or run configured programs
BRANCH_FLAGS = frozenset({"--show-current", "-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "--list", "--no-color"})
TAIL = 4000
NAME = "run_shell"
DESCRIPTION = ("Run one program in the project workspace and return its stdout, stderr and exit code. The command is split "
               "into arguments and run without a shell: no pipes, &&, redirects, globs or $VARIABLES. Allowed programs: node, "
               "npx, npm, python, python3, pytest, and git with a read-only verb (status, log, diff, show, ls-files, rev-parse, "
               "branch). Write plugin script paths in full. Each command waits for the user's approval.")


def refusal(argv: list[str]) -> str | None:
    """Why this argument list may not run, or None when it may."""
    if not argv:
        return "The command is empty"
    program = argv[0]
    if program not in PROGRAMS:
        return f"{program} is not allowed. The harness shell runs only: {', '.join(sorted(PROGRAMS))} (by name, without a path)"
    if program != "git":
        return None
    verb = argv[1] if len(argv) > 1 else ""
    if verb not in GIT_READ:
        return f"git {verb or '(no verb)'} is not allowed. git runs only the read-only verbs {', '.join(sorted(GIT_READ))}, with the verb first"
    if any(a.startswith(GIT_REFUSED_FLAGS) for a in argv[2:]):
        return f"git {verb} with {', '.join(GIT_REFUSED_FLAGS)} is not allowed"
    if verb == "branch" and any(a not in BRANCH_FLAGS for a in argv[2:]):
        return f"git branch only lists branches here; allowed flags: {', '.join(sorted(BRANCH_FLAGS))}"
    return None


def instructions(snapshot) -> str:
    """ShellEnvironmentProvider's block, rewritten for an argument-list runner (MAF's default text describes bash idioms)."""
    return (f"## Shell\n`{NAME}` runs one allowlisted program as an argument list in {snapshot.working_directory or 'the project workspace'}. "
            "There is no shell: write `node /full/path/script.ts --flag value`, never pipes, `&&`, `cd`, redirects or variables. "
            "Each command waits for the user's approval.")


class WorkspaceShell(LocalShellTool):
    def __init__(self, workspace):
        super().__init__(mode="stateless", workdir=workspace.root, clean_env=True, env={}, timeout=HARNESS_SHELL_TIMEOUT)
        self.workspace = workspace

    def options(self) -> ShellEnvironmentProviderOptions:
        return ShellEnvironmentProviderOptions(probe_tools=(), instructions_formatter=instructions)

    def as_function(self, *, name: str = NAME, description: str | None = DESCRIPTION):
        tool = super().as_function(name=name, description=description)
        # MAF's parser keeps its str subclass inside the Content, which FileHistoryProvider cannot serialize (found in the live run)
        tool.result_parser = lambda result: [Content.from_text(str(result))]
        return tool

    async def run(self, command: str, *, timeout: float | None = None) -> ShellResult:
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise ShellCommandError(f"Command rejected: {exc}") from exc
        if reason := refusal(argv):
            raise ShellCommandError(f"Command rejected: {reason}. Nothing ran.")
        ws, started = self.workspace, time.perf_counter()
        seconds = int(timeout if timeout is not None else self._timeout)
        out = await asyncio.to_thread(sandbox.execute_command, ws.project_id, argv, cwd=ws.root, timeout=seconds, extra_env=ws.env())
        took = int((time.perf_counter() - started) * 1000)
        stdout, stderr = out.get("stdout") or "", out.get("stderr") or out.get("message") or ""
        exit_code = out.get("exit_code") if isinstance(out.get("exit_code"), int) else -1
        timed_out = out.get("status") == "timeout"
        ledger.append(ws.project_id, "agent:harness", "harness.shell", ws.thread_id, {
            "command": redact(shlex.join(argv)), "exit_code": exit_code, "timed_out": timed_out, "ms": took, "user": ws.user_id,
            "stdout_tail": redact(stdout)[-TAIL:], "stderr_tail": redact(stderr)[-TAIL:]})
        return ShellResult(stdout=redact(stdout)[-64000:], stderr=redact(stderr)[-64000:], exit_code=exit_code, duration_ms=took,
                           truncated=len(stdout) > 64000 or len(stderr) > 64000, timed_out=timed_out)


class ShellProvider(ShellEnvironmentProvider):
    """MAF's shell environment provider, which also adds the shell tool on every run. A tool a provider adds is approved
    through MAF's ToolApprovalMiddleware on resume; a static agent tool is not (AG-UI 1.7.1 refuses "local approval
    execution with context providers"), which is also why `create_harness_agent(shell_executor=...)` is not used."""

    def __init__(self, shell: WorkspaceShell):
        super().__init__(shell, shell.options())
        self.tool = shell.as_function()

    async def before_run(self, *, agent, session, context, state) -> None:
        await super().before_run(agent=agent, session=session, context=context, state=state)
        context.extend_tools(self.source_id, [self.tool])
