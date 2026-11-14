"""Eval rules turned into MAF checks."""
from __future__ import annotations

import re

from agent_framework import evaluator
from pydantic import ValidationError

from backend.core import gherkin
from backend.maf import runtime as agents
from backend.qe import model
from backend.rag.schemas import DocumentAnswer


def _schemas() -> dict:
    from backend.maf import workflows

    return {"Review": workflows.Review, "ReviewFindings": workflows.ReviewFindings, "GeneratedSuite": workflows.GeneratedSuite, "RequirementSet": model.RequirementSet,
            "TestPlan": model.TestPlan, "CaseSet": model.CaseSet, "ConfidenceReview": model.ConfidenceReview, "AuditSet": model.AuditSet, "ArchitectureNote": model.ArchitectureNote,
            "DocumentAnswer": DocumentAnswer}


def build_checks(rules: dict) -> list:
    """Each rule becomes one MAF check. Failures name what was wrong."""
    checks = []

    def add(name, fn):
        checks.append(evaluator(fn, name=name))

    for word in rules.get("contains", []):
        add(f"contains:{word}", lambda response, w=word: w.lower() in response.lower())
    for word in rules.get("not_contains", []):
        add(f"not_contains:{word}", lambda response, w=word: w.lower() not in response.lower())
    for word in rules.get("not_only", []):
        add(f"not_only:{word}", lambda response, w=word: response.strip().strip(".").lower() != w.lower())
    for pattern in rules.get("matches", []):
        add(f"matches:{pattern}", lambda response, pat=pattern: re.search(pat, response) is not None)
    if rules.get("gherkin"):
        add("valid_gherkin", lambda response: gherkin.validate(_last_part(response))["valid"])
    if rules.get("json_schema"):
        schema = _schemas()[rules["json_schema"]]

        def valid(response: str) -> bool:
            try:
                schema.model_validate(agents.extract_json(response))
                return True
            except (ValueError, ValidationError):
                return False

        add(f"schema:{rules['json_schema']}", valid)
    if "max_score" in rules:
        add(f"score<={rules['max_score']}", lambda response: _score(response) <= rules["max_score"])
    if "min_score" in rules:
        add(f"score>={rules['min_score']}", lambda response: _score(response) >= rules["min_score"])
    return checks


def _last_part(response: str) -> str:
    text = response.strip().removeprefix("```gherkin").removeprefix("```").removesuffix("```").strip()
    start = next((i for i, line in enumerate(text.splitlines()) if line.lstrip().startswith(("Feature:", "@"))), 0)
    return "\n".join(text.splitlines()[start:])


def _score(response: str) -> int:
    try:
        return int(agents.extract_json(response).get("score", -1))
    except (ValueError, TypeError):
        return -1
