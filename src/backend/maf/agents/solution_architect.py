"""Greenfield: picks the stack template and writes the architecture note for Gate A (docs/QE_V2_PLAN.md section 4). Prompt: prompts/solution-architect.md."""
from backend.maf.agents.policy import AgentPolicy

POLICY = AgentPolicy("Solution architect", "Picks a stack template and maps requirements to modules, data, routes and pages for Gate A", "low", max_tokens=8_000)
