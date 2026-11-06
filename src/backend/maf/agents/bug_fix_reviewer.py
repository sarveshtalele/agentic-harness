"""Scores proposed bug fixes, verifies assertion preservation and AST integrity, and assigns a confidence score.
Prompt: prompts/bug-fix-reviewer.md. Evals: evals/bug-fix-reviewer.json.
"""
from backend.maf.agents.policy import READ, AgentPolicy

POLICY = AgentPolicy(
    "Bug fix reviewer",
    "Scores proposed bug fixes, evaluates assertion preservation, and outputs a confidence score for authentic fixes",
    "medium",
    chat_tools=frozenset(READ | {"list_findings", "remember"}),
)
