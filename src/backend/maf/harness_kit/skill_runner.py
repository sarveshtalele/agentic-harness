"""MAF `script_runner` for skill scripts in every common language (docs/PHASE2_PLAN.md section 7.3 and 7.4).

MAF's `run_skill_script` hands a file script's arguments as a list of strings; this runs the script with the interpreter
`core/script_runtime.plan` finds (Python, TypeScript, JavaScript, Bash, PowerShell, Ruby, Go, or what its shebang names),
as an argument list, no shell, a timeout and a clean environment with `CLAUDE_SKILL_DIR` and `CLAUDE_PROJECT_DIR` set.
A Skill Studio script skill keeps its contract: `scripts/run.py` gets the input on standard input, in a temporary copy.
Before the first run of a skill its health is checked with a smoke run (`core/script_health.py`); a flagged script is
refused with the reason, and three failed runs in a row flag it. The call already waited for the human's approval card.
On the web profile skill code is refused with the reason (Studio's `check_profile`).
"""
from __future__ import annotations

import asyncio
import json
import shlex
from pathlib import Path

from agent_framework import ContextProvider

from backend.core import ledger, script_health
from backend.core import script_runtime as rt
from backend.core.security import redact
from backend.core.skill_studio import testing
from backend.repos.sandbox import clean_sandbox_env

ENTRY = "scripts/run.py"
FAILS_TO_FLAG = 3
_failures: dict[str, int] = {}  # skill content hash -> failed runs in a row; ponytail: per process


def _input(args) -> str:
    """Standard input for a Studio `scripts/run.py` from the tool call's arguments."""
    if args is None:
        return ""
    if isinstance(args, str):
        return args
    if isinstance(args, dict):
        given = args.get("input", args.get("stdin"))
        return given if isinstance(given, str) else json.dumps(given if given is not None else args)
    return "\n".join(str(a) for a in args)


def _argv(args) -> tuple[list[str], str]:
    """(command-line arguments, standard input) for any other script."""
    if args is None:
        return [], ""
    if isinstance(args, str):
        return shlex.split(args), ""
    if isinstance(args, dict):
        stdin = args.get("input", args.get("stdin", ""))
        flags = []
        for key, value in args.items():
            if key in ("input", "stdin") or value is None or value is False:
                continue
            flags += [f"--{key}"] if value is True else [f"--{key}", str(value)]
        return flags, stdin if isinstance(stdin, str) else json.dumps(stdin)
    return [str(a) for a in args], ""


def runner(ws=None):
    """A runner for one harness turn; `ws` is the conversation's workspace, or None without a repository."""

    async def run_skill_script(skill, script, args) -> str:
        folder = Path(skill.path)
        name = _name(skill)
        target = Path(script.full_path).resolve()
        relative = target.relative_to(folder.resolve()).as_posix()
        try:
            testing.check_profile()
        except testing.ProfileRefused as exc:
            return str(exc)
        if relative == ENTRY:  # a Skill Studio script skill: input on standard input, exactly as the Studio tests it
            done = await asyncio.to_thread(testing.run_entry, folder, _input(args))
            if done["exit_code"] == 0:
                return done["output"]
            return f"{ENTRY} failed (exit code {done['exit_code']}). Output:\n{done['output']}\nErrors:\n{done['detail']}"
        report = await asyncio.to_thread(script_health.check_skill, folder, smoke=True)
        mine = next((r for r in report["scripts"] if r["script"] == relative), None)
        if mine is None or mine["verdict"] == "flagged" or report.get("runtime_flag"):
            why = report.get("runtime_flag") or (mine["reason"] if mine else "not a script of this skill")
            return f"Refused: the skill {name} is flagged ({relative}: {why}). Nothing ran. Tell the user why; do not work around it."
        md = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace") if (folder / "SKILL.md").is_file() else ""
        plan = rt.plan(target, folder, md)
        extra, stdin = _argv(args)
        env = clean_sandbox_env({**(ws.env() if ws else {}), "CLAUDE_SKILL_DIR": str(folder), "AQH_SKILL_DIR": str(folder),
                                 **({"CLAUDE_PROJECT_DIR": str(ws.root)} if ws else {})})
        done = await asyncio.to_thread(rt.run, [*plan.argv, *extra], cwd=ws.root if ws else folder, env=env, stdin=stdin)
        _count(report, folder, done["exit_code"], relative)
        if ws is not None:
            ledger.append(ws.project_id, "agent:harness", "harness.skill_script", f"{name}/{relative}",
                          {"language": plan.language, "exit_code": done["exit_code"], "args": redact(" ".join(extra))[:500], "user": ws.user_id})
        out = redact(done["stdout"] or "")
        err = redact(done["stderr"] or "")
        tail = f"\n[stderr]\n{err[-4000:]}" if err.strip() else ""
        return f"{out[-30000:]}{tail}\n\n{plan.language} script {relative}: exit code {done['exit_code']}".strip()

    return run_skill_script


def _name(skill) -> str:
    """MAF's FileSkill keeps its name in the frontmatter (found in the 2026-11-13 eval: `.name` does not exist)."""
    front = getattr(skill, "frontmatter", None)
    return str(getattr(front, "name", None) or getattr(skill, "name", None) or Path(skill.path).name)


def _count(report: dict, folder: Path, exit_code, relative: str) -> None:
    key = report["hash"]
    _failures[key] = 0 if exit_code == 0 else _failures.get(key, 0) + 1
    if _failures[key] >= FAILS_TO_FLAG:
        script_health.flag_runtime(folder, report, f"{relative} failed {FAILS_TO_FLAG} runs in a row")


run_skill_script = runner(None)  # for callers without a workspace (and older imports)


def skill_dirs(paths: list) -> list[Path]:
    found = []
    for root in map(Path, paths):
        if (root / "SKILL.md").is_file():
            found.append(root)
        elif root.is_dir():
            found += [d for d in root.iterdir() if (d / "SKILL.md").is_file()]
    return found


class SkillHealthProvider(ContextProvider):
    """Before each run: skills whose scripts cannot run here, with the reason. Uses cached checks; skills not checked yet
    are checked in the background without executing anything."""

    def __init__(self, paths: list, note: str = ""):
        super().__init__("skill_health")
        self.paths, self.note = paths, note

    async def before_run(self, *, agent, session, context, state) -> None:
        if self.note:  # repository skills are repository content
            context.extend_instructions(self.source_id, self.note)
        dirs = skill_dirs(self.paths)
        script_health.refresh_in_background(dirs)
        flagged = [(d.name, r) for d in dirs if (r := script_health.cached_report(d)) and r["verdict"] == "flagged"]
        if flagged:
            lines = [f"- {name}: {r.get('runtime_flag') or script_health.reason(r)}" for name, r in flagged]
            context.extend_instructions(self.source_id, "## Flagged skills (their scripts cannot run here; do not use them; tell the "
                                        "user why)\n" + "\n".join(lines))
