"""The skills catalog: read-only for any signed-in account. Creating, testing and publishing skills is the Skill Studio (api/skill_studio.py)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core import skills

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
    }


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
