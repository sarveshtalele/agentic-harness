"""Real Bash and PowerShell for the harness (docs/PHASE2_PLAN.md section 5; CLAUDE.md D-SHELL exception, 2026-11-12).

Built on MAF's `LocalShellTool` in persistent mode: one shell process per conversation and shell kind, so `cd` and
variables carry from one command to the next, as in Claude Code. Shells found per platform:
- `bash`: /bin/bash on macOS and Linux; on Windows Git for Windows' bash.exe (never System32\\bash.exe, which is WSL);
- `powershell`: pwsh (PowerShell 7+) anywhere, else Windows PowerShell 5.1 on Windows.
Each command: approval card (or a permission rule, `permissions.py`), plugin hooks with Claude Code's tool names, a
timeout (2 minutes by default, 10 at most), output over 30,000 characters saved to `.aqh/out/` with a preview, exit code 1
treated as normal for search and compare commands, the ledger entry, and a reset note if `cd` left the workspace.
Long jobs and servers go to the background (`bg_tasks.py`). The web profile keeps the allowlisted `run_shell` (D-SHELL-WEB).
"""

import asyncio
import os
import re
import secrets
import shutil
import sys
import time
from pathlib import Path
from typing import Annotated

from agent_framework import tool
from agent_framework_tools.shell import LocalShellTool
from pydantic import Field

from backend.core import ledger
from backend.core.security import redact
from backend.repos.sandbox import clean_sandbox_env

KINDS = ("bash", "powershell")
DEFAULT_MS, MAX_MS = 120_000, 600_000
INLINE, PREVIEW = 30_000, 2_000
BENIGN_EXIT1 = frozenset({"grep", "rg", "egrep", "fgrep", "find", "diff", "test", "["})
CD = re.compile(r"(^|[;&|\s(])(cd|pushd|popd|chdir|Set-Location|Push-Location|Pop-Location|sl)(\s|$|;)", re.I)
_sessions: dict[tuple[str, str], tuple[LocalShellTool, asyncio.AbstractEventLoop]] = {}


def find_bash() -> str | None:
    if os.name != "nt":
        return next((p for p in ("/bin/bash", "/usr/bin/bash") if Path(p).exists()), None) or shutil.which("bash")
    git = shutil.which("git")
    roots = [Path(git).resolve().parent.parent] if git else []
    roots += [Path(os.environ[v]) / "Git" for v in ("ProgramFiles", "ProgramFiles(x86)") if os.environ.get(v)]
    roots += [Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Git"] if os.environ.get("LOCALAPPDATA") else []
    return next((str(r / "bin" / "bash.exe") for r in roots if (r / "bin" / "bash.exe").is_file()), None)


def find_powershell() -> str | None:
    return shutil.which("pwsh") or (shutil.which("powershell") if os.name == "nt" else None)


def available() -> dict[str, str]:
    """{kind: program path} for the shells on this machine."""
    found = {"bash": find_bash(), "powershell": find_powershell()}
    return {k: v for k, v in found.items() if v}


def argv(kind: str, program: str, command: str | None = None) -> list[str]:
    """The program's argument list: a session reading standard input, or one command (`command`) for background tasks."""
    if kind == "bash":
        return [program, "--noprofile", "--norc"] + (["-c", command] if command is not None else [])
    base = [program, "-NoLogo", "-NoProfile", "-NonInteractive"] + (["-ExecutionPolicy", "Bypass"] if os.name == "nt" else [])
    return base + ["-Command", command if command is not None else "-"]


def environment(ws) -> dict[str, str]:
    return clean_sandbox_env({**ws.env(), "AQH_PROJECT_DIR": str(ws.root), "CLAUDE_PROJECT_DIR": str(ws.root)})


async def session(ws, kind: str) -> LocalShellTool:
    """This conversation's shell of this kind, started on first use (and again if its event loop changed)."""
    key, loop = (ws.thread_id, kind), asyncio.get_running_loop()
    found = _sessions.get(key)
    if found and found[1] is loop:
        return found[0]
    program = available().get(kind)
    if not program:
        raise FileNotFoundError(f"No {kind} on this machine" + (" (install Git for Windows for bash)" if kind == "bash" and os.name == "nt" else ""))
    shell = LocalShellTool(mode="persistent", shell=argv(kind, program), workdir=str(ws.root), confine_workdir=False, env=environment(ws),
                           timeout=None, max_stdout_bytes=1 << 20, max_stderr_bytes=256 << 10, approval_mode="always_require")
    await shell.start()
    _sessions[key] = (shell, loop)
    return shell


async def close_thread(thread_id: str) -> None:
    for key in [k for k in _sessions if k[0] == thread_id]:
        shell, loop = _sessions.pop(key)
        if loop is asyncio.get_running_loop():
            await shell.close()


def _first_program(command: str) -> str:
    words = command.strip().split()
    return os.path.basename(words[0]) if words else ""


def _spill(ws, text: str) -> str:
    folder = Path(ws.root) / ".aqh" / "out"
    folder.mkdir(parents=True, exist_ok=True)
    exclude = Path(ws.root) / ".git" / "info" / "exclude"
    if exclude.parent.is_dir() and ".aqh/" not in (exclude.read_text(encoding="utf-8") if exclude.is_file() else ""):
        with exclude.open("a", encoding="utf-8") as f:
            f.write("\n.aqh/\n")  # harness outputs never show up as repository changes
    path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}.txt"
    path.write_text(text, encoding="utf-8")
    return path.relative_to(ws.root).as_posix()


def render(ws, kind: str, command: str, result, timeout_s: float, note: str = "") -> str:
    out, err = redact(result.stdout or ""), redact(result.stderr or "")
    body = out + (f"\n[stderr]\n{err}" if err.strip() else "")
    if len(body) > INLINE:
        saved = _spill(ws, body)
        body = f"{body[:PREVIEW]}\n\n[harness] Output was {len(body)} characters; all of it is saved in {saved}. Read it with read_file or grep it."
    code = result.exit_code
    if result.timed_out:
        status = (f"Timed out after {timeout_s:g} s and was stopped. For a server or a long job, call {kind} again with "
                  "run_in_background=true, or with a larger timeout_ms (up to 600000).")
    elif code == 1 and (_first_program(command) in BENIGN_EXIT1 or command.strip().startswith(("git diff", "git grep"))):
        status = "exit code 1 (no matches or a difference found; not an error)"
    else:
        status = f"exit code {code}"
    if result.truncated:
        status += " (output passed 1 MiB and was cut)"
    return f"{body.rstrip()}\n\n{status}{note}".lstrip()


async def run(ws, kind: str, command: str, timeout_ms: int | None = None) -> str:
    shell = await session(ws, kind)
    timeout_s = min(max(timeout_ms or DEFAULT_MS, 1000), MAX_MS) / 1000
    started = time.perf_counter()
    result = await shell.run(command, timeout=timeout_s)
    note = await _keep_inside(ws, kind, shell) if CD.search(command) else ""
    text = render(ws, kind, command, result, timeout_s, note)
    ledger.append(ws.project_id, "agent:harness", f"harness.{kind}", ws.thread_id, {
        "command": redact(command)[:2000], "exit_code": result.exit_code, "timed_out": result.timed_out,
        "ms": int((time.perf_counter() - started) * 1000), "user": ws.user_id, "output_tail": redact(text)[-2000:]})
    return text


async def _keep_inside(ws, kind: str, shell: LocalShellTool) -> str:
    probe = "pwd" if kind == "bash" else "(Get-Location).Path"
    where = (await shell.run(probe, timeout=10)).stdout.strip().splitlines()
    root = Path(ws.root).resolve()
    try:
        inside = bool(where) and (Path(where[-1]).resolve() == root or root in Path(where[-1]).resolve().parents)
    except (OSError, ValueError):
        inside = False
    if inside:
        return ""
    back = f"cd -- '{root}'" if kind == "bash" else f"Set-Location -LiteralPath '{root}'"
    await shell.run(back, timeout=10)
    return f"\nShell cwd was reset to {root} (commands stay inside the workspace)."


def tools(ws) -> list:
    """`bash` and `powershell` for this workspace, only for the shells installed here. Each asks for approval."""
    from backend.maf.harness_kit import bg_tasks

    made = []
    for kind, program in available().items():
        made.append(_tool(ws, kind, program, bg_tasks))
    return made


def _tool(ws, kind: str, program: str, bg_tasks):
    label = "Bash" if kind == "bash" else "PowerShell"
    where = f"{program} ({sys.platform})"

    async def call(command: Annotated[str, Field(description=f"The {label} command to run in the workspace.")],
                   description: Annotated[str, Field(description="What this command does, in 5 to 10 words (shown on the approval card).", max_length=200)] = "",
                   timeout_ms: Annotated[int | None, Field(description="Timeout in milliseconds, default 120000, at most 600000.", ge=1000, le=MAX_MS)] = None,
                   run_in_background: Annotated[bool, Field(description="Start it in the background (servers, watchers, long jobs) and return at once.")] = False) -> str:
        if run_in_background:
            return bg_tasks.start(ws, kind, program, command, description, timeout_ms)
        return await run(ws, kind, command, timeout_ms)

    return tool(func=call, name=kind, approval_mode="always_require",
                description=(f"Run a {label} command in a persistent {label} session in the project workspace ({where}). `cd` and variables "
                             "carry to the next call; pipes, &&, redirects and scripts work. Output over 30,000 characters is saved to a file. "
                             "Use run_in_background for servers and long jobs, then task_output and task_stop."))
