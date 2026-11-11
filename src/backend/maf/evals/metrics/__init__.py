"""Deterministic, free evaluation metrics. A metric with nothing to measure has the value None, never 0 and never 1."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from agent_framework import evaluator

from backend.maf.evals.metrics.cites import PATH_LINE, _check_one, _context_files, citations, groundedness
from backend.maf.evals.metrics.mutants import SKIP_COPY, mutation_score
from backend.maf.evals.metrics.ratios import at_location, coverage, f1, has_keywords, match, precision, ratio, recall


def metric_check(name: str, measure: Callable[[str], float | None], threshold: float = 0.5):
    """A MAF @evaluator check around one measure. MAF checks are pass or fail, so nothing to measure fails with the reason "Not measured"; the number itself is `measure`'s."""

    def check(response: str) -> dict:
        value = measure(response)
        if value is None:
            return {"score": 0.0, "passed": False, "reason": f"Not measured: {name} has nothing to measure in this reply"}
        return {"score": value, "passed": value >= threshold, "reason": f"{name}={value:.3f}"}

    return evaluator(check, name=name)


def groundedness_check(*, root: Path | None = None, context: str = ""):
    return metric_check("groundedness", lambda reply: groundedness(reply, root=root, context=context)["value"], threshold=1.0)


__all__ = ["PATH_LINE", "SKIP_COPY", "_check_one", "_context_files", "at_location", "citations", "coverage", "f1", "groundedness", "groundedness_check", "has_keywords", "match", "metric_check",
           "mutation_score", "precision", "ratio", "recall"]
