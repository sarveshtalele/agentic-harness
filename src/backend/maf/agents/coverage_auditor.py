"""Checks that each designed case really covers the plan scenario it names (the agentic-qe plugin's coverage-auditor). Prompt: prompts/coverage-auditor.md."""
from backend.maf.agents.policy import AgentPolicy

POLICY = AgentPolicy("Coverage auditor", "Checks that each designed case covers the plan scenario it names", "low", max_tokens=4_000)
