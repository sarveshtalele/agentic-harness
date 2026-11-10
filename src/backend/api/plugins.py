"""Plugins API: what is installed, what MAF loaded from it, which skills are slash commands. Read-only."""
from __future__ import annotations

from pathlib import Path

from agent_framework import FileSkillsSource, SkillsSourceContext
from fastapi import APIRouter

from backend.core import plugins as plugin_lib
from backend.core.skills import _run

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


def _describe(plugin: plugin_lib.Plugin) -> dict:
    loaded, failed, commands = 0, [], []
    if plugin.skills_dir:
        got = {Path(s.path).resolve() for s in _run(FileSkillsSource([plugin.skills_dir]).get_skills(SkillsSourceContext(agent=None)))}
        loaded = len(got)
        failed = [f"{md.parent.name}: MAF could not load it" for md in sorted(plugin.skills_dir.glob("*/SKILL.md")) if md.parent.resolve() not in got]
        commands = sorted(plugin_lib.command_skill_names(plugin.skills_dir))
    return {"id": plugin.id, "version": plugin.version, "description": plugin.description, "trust": plugin.trust, "source": plugin.source,
            "manifest": plugin.manifest, "problems": plugin.problems, "skills": loaded, "commands": commands, "skill_problems": failed}


@router.get("")
def list_plugins() -> list[dict]:
    return [_describe(p) for p in plugin_lib.discover()]
