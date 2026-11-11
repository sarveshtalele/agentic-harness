"""The typed shapes the model must return, and the name, path and content rules the server enforces on them.

`plan_schema` and `files_schema` add the rules that depend on the request (kind, taken names, the approved plan), so a
model reply that breaks one is rejected inside AgentCall.typed and the reason goes back to the model for a retry.
"""
from __future__ import annotations

import re
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.core.skill_studio.checks import NAME_RULE, frontmatter

KINDS = ("instructions", "scripts")
SEGMENT = r"[A-Za-z0-9_][A-Za-z0-9._-]*"
PATHS = {
    "instructions": re.compile(rf"^(SKILL\.md|references/{SEGMENT}\.md|assets/{SEGMENT})$"),
    "scripts": re.compile(rf"^(SKILL\.md|references/{SEGMENT}\.md|assets/{SEGMENT}|scripts/[A-Za-z0-9_]+\.py)$"),
}
TEST_FILE = re.compile(r"^scripts/test_[A-Za-z0-9_]+\.py$")
# ponytail: a pronoun list, not a grammar check; it catches "I will" and "you can", the usual first and second person slips
PERSONAL = re.compile(r"\b(I|me|my|we|our)\b|\b(you|your)\b", re.I)


class PlanFile(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=500)


class Subagent(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=500)
    when: str = Field(min_length=1, max_length=500)


class OutputFormat(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=500)
    template_path: str = Field(pattern=rf"^assets/{SEGMENT}$")


class Assertion(BaseModel):
    kind: Literal["contains", "not_contains", "regex"]
    value: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _regex_compiles(self):
        if self.kind == "regex":
            try:
                re.compile(self.value)
            except re.error as exc:
                raise ValueError(f"regex {self.value!r} does not compile: {exc}") from None
        return self


class EvalCase(BaseModel):
    input: str = Field(min_length=1, max_length=4000)
    assertions: list[Assertion] = Field(min_length=1, max_length=10)


class SkillPlan(BaseModel):
    name: str = Field(max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    tasks: list[str] = Field(min_length=1)
    files: list[PlanFile] = Field(min_length=1)
    subagents: list[Subagent] = []
    formats: list[OutputFormat] = []
    eval_cases: list[EvalCase] = Field(min_length=2, max_length=6)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not NAME_RULE.fullmatch(value):
            raise ValueError("name must be lowercase letters and digits joined by single hyphens")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        if "use when" not in value.lower():
            raise ValueError('description must say when to use the skill, with the words "Use when"')
        if PERSONAL.search(value):
            raise ValueError("description must be in the third person (no I, we, you)")
        return value.strip()


def _squash(text: str) -> str:
    return " ".join(text.split()).lower()


def plan_problems(plan: SkillPlan, kind: str, taken: set[str], source_text: str, revise: str = "") -> list[str]:
    """Rules that need the request: kind, names already used, and the source the eval inputs must come from."""
    problems = []
    if revise and plan.name != revise:
        problems.append(f"name must stay {revise!r}: this plan revises that skill")
    elif not revise and plan.name in taken:
        problems.append(f"name {plan.name!r} is already a skill; choose a new name")
    paths = [f.path for f in plan.files]
    if len(set(paths)) != len(paths):
        problems.append("files lists a path more than once")
    problems += [f"path {p!r} is not allowed when kind is {kind}" for p in paths if not PATHS[kind].match(p)]
    if "SKILL.md" not in paths:
        problems.append("files must include SKILL.md")
    if kind == "scripts" and not any(TEST_FILE.match(p) for p in paths):
        problems.append("a scripts skill needs at least one scripts/test_*.py pytest file")
    if kind == "scripts" and "scripts/run.py" not in paths:  # evaluation runs the skill through it
        problems.append("a scripts skill needs scripts/run.py: read the input from standard input, print the output")
    problems += [f"format {f.name!r} uses {f.template_path}, which is not in files" for f in plan.formats if f.template_path not in paths]
    source = _squash(source_text)
    # an input is a realistic example the skill would receive, never the source's own rules (live run 2026-11-10 measured that as uplift -0.375)
    problems += [f"eval case {i} input repeats the source; give a realistic input the skill would receive" for i, c in enumerate(plan.eval_cases, 1)
                 if len(_squash(c.input)) > 40 and _squash(c.input) in source and len(_squash(c.input)) > len(source) // 2]
    return problems


def plan_schema(kind: str, taken: set[str], source_text: str, revise: str = "") -> type[SkillPlan]:
    class CheckedPlan(SkillPlan):
        @model_validator(mode="after")
        def _request_rules(self):
            if problems := plan_problems(self, kind, taken, source_text, revise):
                raise ValueError("; ".join(problems))
            return self

    CheckedPlan.__name__ = "SkillPlan"
    return CheckedPlan


class GeneratedFile(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=200_000)


class GeneratedFiles(BaseModel):
    files: list[GeneratedFile] = Field(min_length=1)


def files_problems(files: GeneratedFiles, plan: SkillPlan, kind: str, author: str) -> list[str]:
    planned = {f.path for f in plan.files}
    paths = [f.path for f in files.files]
    problems = [f"path {p!r} is not in the approved plan" for p in paths if p not in planned]
    problems += [f"path {p!r} is not allowed when kind is {kind}" for p in paths if p in planned and not PATHS[kind].match(p)]
    if len(set(paths)) != len(paths):
        problems.append("a path is written more than once")
    if kind == "scripts" and not any(TEST_FILE.match(p) for p in paths):
        problems.append("a scripts skill needs at least one scripts/test_*.py pytest file")
    skill_md = next((f.content for f in files.files if f.path == "SKILL.md"), None)
    if skill_md is None:
        return problems + ["SKILL.md is required"]
    front, _ = frontmatter(skill_md)
    if front is None:
        return problems + ["SKILL.md must start with YAML frontmatter"]
    meta = front.get("metadata") if isinstance(front.get("metadata"), dict) else {}
    if front.get("name") != plan.name:
        problems.append(f"frontmatter name must be {plan.name!r}")
    if str(front.get("description", "")).strip() != plan.description:
        problems.append("frontmatter description must be the approved description, word for word")
    if "version" in front or "version" in meta:
        problems.append("frontmatter must not carry a version: the server numbers versions on publish")
    for found in (front.get("author"), meta.get("author")):
        if found is not None and str(found) != author:
            problems.append(f"author may only be {author!r}, the signed-in user")
    return problems


def canonical_skill_md(content: str, plan: SkillPlan, author: str) -> str:
    """SKILL.md with frontmatter written by the server from the approved plan, and the model's body kept.

    The name and description must equal the plan word for word, so the server owns them and quotes them as YAML.
    A model that wrote an unquoted colon in the description broke the YAML three times in a row (owner report
    2026-11-11); writing it here removes that failure. The author is the signed-in user; no version is written."""
    text = content.lstrip("\ufeff \n")
    body = text
    if text.startswith("---") and "\n---" in text[3:]:
        rest = text[3:].split("\n---", 1)[1]
        body = rest.split("\n", 1)[1] if "\n" in rest else ""
    head = {"name": plan.name, "description": plan.description, "metadata": {"author": author}}
    return "---\n" + yaml.safe_dump(head, sort_keys=False, allow_unicode=True, width=100_000) + "---\n" + body.lstrip("\n")


def files_schema(plan: SkillPlan, kind: str, author: str) -> type[GeneratedFiles]:
    class CheckedFiles(GeneratedFiles):
        @model_validator(mode="after")
        def _plan_rules(self):
            for item in self.files:
                if item.path == "SKILL.md":
                    item.content = canonical_skill_md(item.content, plan, author)
            if problems := files_problems(self, plan, kind, author):
                raise ValueError("; ".join(problems))
            return self

    CheckedFiles.__name__ = "GeneratedFiles"
    return CheckedFiles
