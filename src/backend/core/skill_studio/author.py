"""Every Skill Studio model call, through MAF's AgentCall with the skill-creator policy and its versioned prompt."""
from __future__ import annotations

import json

from backend.core.errors import ModelJsonError, ModelSchemaError, ModelTruncated
from backend.core.security import redact
from backend.core.skill_studio import plans
from backend.core.skill_studio.models import SkillPlan, files_schema, plan_schema
from backend.core.skill_studio.source import data_block
from backend.db import new_id

AGENT = "skill-creator"
KIND_RULES = {
    "instructions": "KIND: instructions. Files are SKILL.md, optional references/*.md, and optional assets/* templates. No scripts.",
    "scripts": "KIND: scripts. Files are SKILL.md, scripts/*.py with real code, scripts/run.py (the entry point: it reads the input as text from "
               "standard input and prints the skill's output to standard output), and at least one scripts/test_*.py pytest file that imports "
               "the script by module name and asserts real behaviour. Optional references/*.md and assets/* templates.",
}


class ReplyRejected(Exception):
    """The model's reply failed validation after its retries. Answered 502; the reply is kept on disk for debugging."""

    def __init__(self, message: str, reply_file: str):
        super().__init__(message)
        self.message, self.reply_file = message, reply_file


def _call(project_id: str):
    from backend.maf.runtime import AgentCall  # late: maf imports core

    return AgentCall(None, project_id, AGENT, skills=(), source="skill-studio")


def _keep(exc: Exception) -> str:
    """The rejected reply goes to a file, redacted, as workflow failures do under data/runs/<run>/failures/."""
    folder = plans.drafts_root() / "failures"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{new_id('rep')}.txt"
    path.write_text(redact(str(getattr(exc, "detail", {}).get("reply", ""))), encoding="utf-8")
    return path.name


async def _typed(call, message: str, schema):
    try:
        return await call.typed(message, schema)
    except (ModelJsonError, ModelSchemaError, ModelTruncated) as exc:
        raise ReplyRejected(str(exc), _keep(exc)) from exc


def _skill_names() -> set[str]:
    from backend.core import skills

    return set(skills.load())


async def propose_plan(project_id: str, kind: str, request: str, source: dict, revise: str = "") -> tuple[SkillPlan, str]:
    taken = _skill_names()
    message = "\n".join([
        "TASK: plan a new agent skill.",
        KIND_RULES[kind],
        f"REQUEST from the signed-in user: {request.strip() or '(none: plan the skill the source describes)'}",
        f"REVISING the existing skill {revise!r}: keep that name." if revise else f"Names already used, which the new name must avoid: {', '.join(sorted(taken)) or 'none'}.",
        "Each eval case input is a realistic example of what a user gives the skill, not the source's own rules.",
        data_block("source", source["text"]),
    ])
    call = _call(project_id)
    plan = await _typed(call, message, plan_schema(kind, taken, source["text"], revise))
    return SkillPlan.model_validate(plan.model_dump()), call.prompt_ref


async def write_files(plan: dict, author: str) -> list[dict]:
    approved = SkillPlan.model_validate(plan["plan"])
    message = "\n".join([
        "TASK: write every file of the approved skill plan.",
        KIND_RULES[plan["kind"]],
        "Write exactly the files the plan lists, by path. SKILL.md starts with YAML frontmatter holding name and description copied from the plan, "
        f"and no version. If you add an author, it is {author!r}.",
        "APPROVED PLAN:",
        json.dumps(plan["plan"], indent=1),
        data_block("source", plan["source_text"]),
    ])
    generated = await _typed(_call(plan["project_id"]), message, files_schema(approved, plan["kind"], author))
    return [{"path": f.path, "content": f.content} for f in generated.files]


async def repair_files(plan: dict, author: str, files: list[dict], failure: str) -> list[dict]:
    """One repair round: the current files and the failing test output go back to the model, which returns every file."""
    approved = SkillPlan.model_validate(plan["plan"])
    message = "\n".join([
        "TASK: repair the files of the approved skill plan; its own tests failed.",
        KIND_RULES[plan["kind"]],
        "APPROVED PLAN:", json.dumps(plan["plan"], indent=1),
        "CURRENT FILES:", json.dumps(files, indent=1),
        data_block("test-output", failure),
        data_block("source", plan["source_text"]),
    ])
    repaired = await _typed(_call(plan["project_id"]), message, files_schema(approved, plan["kind"], author))
    return [{"path": f.path, "content": f.content} for f in repaired.files]


def skill_text(files: list[dict], name: str) -> str:
    """The draft's SKILL.md and references, given to the model as the instructions under test."""
    parts = [f'<skill-under-test name="{name}">\n{next(f["content"] for f in files if f["path"] == "SKILL.md")}\n</skill-under-test>']
    parts += [f'<reference file="{f["path"]}">\n{f["content"]}\n</reference>' for f in files if f["path"].startswith("references/")]
    return "\n".join(parts)


async def apply(project_id: str, sample: str, *, skill: str = "", description: str = "") -> dict:
    """One model call on a sample. With `skill`, the draft is the instructions; without it, only the description, as an agent sees before it loads a skill."""
    task = (f"TASK: apply the skill under test to the input below and reply with its output.\n{skill}" if skill
            else f"TASK: handle the input below for this purpose: {description}")
    call = _call(project_id)
    output = await call.text(f"{task}\n{data_block('input', sample)}", tools_allowed=False)
    return {"output": output, "tokens_in": call.last_call.get("tokens_in", 0), "tokens_out": call.last_call.get("tokens_out", 0), "prompt_ref": call.prompt_ref}
