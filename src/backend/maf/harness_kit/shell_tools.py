"""The harness's shell tools on CLI, desktop and local profiles (docs/PHASE2_PLAN.md section 5): `bash`, `powershell`,
`task_output`, `task_stop`, and a short note of the machine's shells and tool versions (MAF's ShellEnvironmentProvider
idea, probed once per process). Tools come through a context provider because AG-UI approves only provider tools on
resume (see shell.py). The web profile keeps the allowlisted `run_shell` instead (D-SHELL-WEB).
"""
from __future__ import annotations

import functools
import platform
import subprocess

from agent_framework import ContextProvider

from backend.maf.harness_kit import bg_tasks, shells

PROBES = ("git", "node", "python", "pwsh", "npm")


@functools.cache
def versions() -> dict[str, str]:
    import shutil

    found = {}
    for name in PROBES:
        program = shutil.which(name) or (shutil.which("python3") if name == "python" else None)
        if not program:
            continue
        try:
            out = subprocess.run([program, "--version"], capture_output=True, text=True, timeout=5, check=False, stdin=subprocess.DEVNULL)
            found[name] = (out.stdout or out.stderr).strip().splitlines()[0][:60] if (out.stdout or out.stderr).strip() else "present"
        except (OSError, subprocess.TimeoutExpired):
            continue
    return found


def note(ws) -> str:
    have = shells.available()
    lines = [f"## Shells on this machine ({platform.system()} {platform.release()})"]
    if not have:
        lines.append("No bash or PowerShell was found, so no shell tool is available.")
    for kind, program in have.items():
        lines.append(f"- `{kind}`: {program}")
    if "bash" not in have and "powershell" in have:
        lines.append("- No bash here (on Windows, install Git for Windows to get it), so .sh scripts cannot run; use PowerShell.")
    if v := versions():
        lines.append("Tools: " + "; ".join(f"{k} {val}" for k, val in v.items()))
    lines.append(f"Working directory: the workspace {ws.root}. Shells keep `cd` and variables between calls. Run skill scripts with the "
                 "interpreter their SKILL.md names (python, node for .ts/.js, bash for .sh, pwsh for .ps1); Node 22.18 or newer runs a .ts "
                 "file directly (`node scripts/x.ts`), so no tsx, npx or install is needed. Use run_in_background for "
                 "servers and watchers, then task_output and task_stop.")
    return "\n".join(lines)


class ShellToolsProvider(ContextProvider):
    def __init__(self, ws):
        super().__init__("shell_tools")
        self.ws = ws
        self.tools = shells.tools(ws) + bg_tasks.tools(ws)

    async def before_run(self, *, agent, session, context, state) -> None:
        context.extend_tools(self.source_id, self.tools)
        context.extend_instructions(self.source_id, note(self.ws))
