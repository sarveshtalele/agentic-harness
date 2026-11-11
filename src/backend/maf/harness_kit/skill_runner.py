"""MAF `script_runner` for skills in the harness (found live 2026-11-11: a published script skill could not run).

Without a runner MAF's `run_skill_script` answers "requires a runner", and the model went on to make duplicate skills.
A script skill made in Skill Studio has one entry point, `scripts/run.py`: input on standard input, result on standard
output. This runs it exactly as Skill Studio tests it (`skill_studio.testing.run_entry`): a temporary copy of the skill,
the platform's Python, a clean environment, a timeout, no shell. The call already waited for the human's approval card
(MAF's `run_skill_script` requires approval). Untrusted code runs only in the local and desktop profiles; on the web it
is refused with the reason. Other script names are refused, so a plugin skill's own runners are not started this way.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.core.skill_studio import testing

ENTRY = "scripts/run.py"


def _input(args) -> str:
    """The script's standard input from the tool call's arguments."""
    if args is None:
        return ""
    if isinstance(args, str):
        return args
    if isinstance(args, dict):
        given = args.get("input", args.get("stdin"))
        return given if isinstance(given, str) else json.dumps(given if given is not None else args)
    return "\n".join(str(a) for a in args)


async def run_skill_script(skill, script, args) -> str:
    folder = Path(skill.path)
    relative = Path(script.full_path).resolve().relative_to(folder.resolve()).as_posix()
    if relative != ENTRY:
        return f"Only {ENTRY} runs here (input on standard input). This skill's {relative} is not run by the harness."
    try:
        done = await asyncio.to_thread(testing.run_entry, folder, _input(args))
    except testing.ProfileRefused as exc:
        return str(exc)
    if done["exit_code"] == 0:
        return done["output"]
    return f"{ENTRY} failed (exit code {done['exit_code']}). Output:\n{done['output']}\nErrors:\n{done['detail']}"
