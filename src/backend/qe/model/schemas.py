"""Requirement, plan and review schemas."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator

from backend.qe.model.domain import input_type


CASE_TYPES = ("Positive", "Negative", "Negative (Boundary)", "Exception")


ORACLES = ("specified", "derived", "metamorphic", "golden")


class Requirement(BaseModel):
    id: str
    title: str
    statement: str
    type: Literal["functional", "non-functional", "security", "data", "integration"] = "functional"
    priority: Literal["P0", "P1", "P2"] = "P1"
    tier: Literal["specified", "observed", "inferred"] = "observed"
    actor: Literal["anonymous", "customer", "admin", "system"] = "system"  # plugin rule: exactly one named actor
    file: str = ""
    line: int = 0
    quote: str = ""
    input_type: str = Field("", description="The type of the input the requirement states: string, number, integer, boolean, list or object. Empty when it states none.")
    error_behaviour: str = Field("", description="The error the requirement or code states for bad input, such as 'raises ValueError when b is 0'. Empty when it states none: never invent one.")

    @field_validator("input_type", mode="before")
    @classmethod
    def known_type(cls, value):
        return input_type(value)

    @field_validator("actor", mode="before")
    @classmethod
    def one_actor(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


COMMENT_START = ("#", "//", "/*", "*", "<!--", '"""', "'''")


def is_comment(quote: str) -> bool:
    """Plugin precedence rule: executable code beats comments, so a comment line is not evidence of behaviour."""
    return quote.strip().startswith(COMMENT_START)


class RequirementSet(BaseModel):
    requirements: list[Requirement] = Field(min_length=1)


class PlanArea(BaseModel):
    id: str
    name: str
    requirement_ids: list[str] = Field(min_length=1)
    risk: Literal["P0", "P1", "P2"]
    level: Literal["Unit", "Integration", "E2E"]
    framework: str
    rationale: str


class TestPlan(BaseModel):
    __test__ = False
    strategy: str
    areas: list[PlanArea] = Field(min_length=1)
    skipped_levels: dict[str, str] = Field(default_factory=dict)


class ConfidenceReview(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: Literal["APPROVED", "REVISE", "REJECTED"]
    issues: list[str] = Field(default_factory=list)
