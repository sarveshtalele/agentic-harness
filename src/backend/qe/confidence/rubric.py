"""Confidence rubric, schemas and verdict thresholds."""
from __future__ import annotations

from pydantic import BaseModel, Field


RUBRIC: dict[str, dict[str, int]] = {
    "design": {"source_proven": 30, "correct_target": 25, "expected_derivable": 25, "fixture_validity": 20},
    "code": {"compilable": 30, "assertion_integrity": 30, "import_safety": 20, "traceability_present": 20},
    "plan": {"controls_covered": 40, "level_fit": 30, "scenarios_derivable": 30},
}


THRESHOLD = 70  # under this total a case is low confidence


ASSERTION_FLOOR = 20  # a test whose assertions score under this can pass with the code under test removed, so it is low at any total


MAX_FILE_BYTES = 5 * 1024 * 1024


TEST_FAIL_CAP = 60  # a reviewed test that failed in execution cannot show more than this


RANK = {"APPROVED": 0, "REVISE": 1, "REJECT": 2}


class Component(BaseModel):
    file: str = ""
    line: int = 0
    symbol: str = ""


class Flaw(BaseModel):
    dimension: str = ""
    evidence: str = ""
    fix: str = ""


class Item(BaseModel):
    tc_id: str
    file: str = ""
    component: Component | None = None
    scores: dict[str, int | float | str] = Field(default_factory=dict)
    total: int | float | str | None = 0
    verdict: str = ""
    flaws: list[Flaw] = Field(default_factory=list)


class Review(BaseModel):
    """What the reviewer returns. Every number in it is a claim that `check_item` verifies."""

    kind: str = ""
    items: list[Item] = Field(min_length=1)


def verdict_for(total: int) -> str:
    return "APPROVED" if total == 100 else "REVISE" if total >= THRESHOLD else "REJECT"


def worst(*verdicts: str) -> str:
    return max(verdicts, key=lambda v: RANK.get(v, 2))
