"""Plans and writes Agent Skills in the Skill Studio, and applies a draft skill to a sample. Prompt: prompts/skill-creator.md. Evals: evals/skill-creator.json."""
from backend.maf.agents.policy import AgentPolicy

POLICY = AgentPolicy("Skill creator", "Plans and writes Agent Skills from a project source, and applies a draft skill to a sample", "low")
