"""Shared constants for the skills tests."""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPECTED = {"analyzing-repositories", "authoring-user-stories", "building-qe-dashboard", "designing-test-cases", "executing-tests", "extracting-requirements",
            "generating-test-code", "generating-test-data", "healing-tests", "planning-tests", "tracing-coverage", "skill-creator", "evaluator"}
ARCHITECT = "You are a principal test architect"
