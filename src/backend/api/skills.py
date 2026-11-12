"""The skills catalog: read-only for any signed-in account. Creating, testing and publishing skills is the Skill Studio (api/skill_studio.py)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.config import PROFILE, SKILLS_DIR
from backend.core import script_health, skills

router = APIRouter()


def _summary(skill: skills.Skill) -> dict:
    return {
        "name": skill.name,
        "description": skill.description,
        "version": skill.version,
        "agents": skills.agent_of(skill.name),
        "references": sorted(skill.references),
        "chars": len(skill.body) + sum(len(t) for t in skill.references.values()),
        "sha256": skill.sha256,
        "folder": skill.folder,
        "health": _health(skill),
    }


def _health(skill: skills.Skill, *, refresh: bool = False, smoke: bool = False) -> dict:
    """Can this skill's scripts run here (docs/PHASE2_PLAN.md 7.4)? Static checks only unless an admin asks again."""
    folder = SKILLS_DIR / skill.folder
    if not script_health.scripts_of(folder):
        return {"verdict": "ok", "reason": "no scripts"}
    report = script_health.check_skill(folder, refresh=refresh, smoke=smoke)
    return {"verdict": report["verdict"], "reason": report.get("runtime_flag") or script_health.reason(report),
            "scripts": [{k: r[k] for k in ("script", "language", "verdict", "reason")} for r in report["scripts"]]}


@router.get("/api/skills")
def list_skills():
    return {"skills": [_summary(skills.get(n)) for n in skills.names()], "problems": skills.problems()}


@router.get("/api/skills/{name}")
def get_skill(name: str):
    try:
        skill = skills.get(name)  # a name in the loaded catalog only, never a path
    except KeyError:
        raise HTTPException(404, f"Skill not found: {name}") from None
    return {**_summary(skill), "body": skill.body, "reference_text": skill.references}


@router.post("/api/skills/{name}/health")
def check_skill_again(name: str):
    """Admin: check again, with a smoke run of each script outside the web profile (it executes the scripts)."""
    try:
        skill = skills.get(name)
    except KeyError:
        raise HTTPException(404, f"Skill not found: {name}") from None
    return _health(skill, refresh=True, smoke=PROFILE != "web")

