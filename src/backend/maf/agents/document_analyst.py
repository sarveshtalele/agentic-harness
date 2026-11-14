"""Answers questions about the uploaded requirement documents from retrieved chunks, with citations (QE v2 step 4). Prompt: prompts/document-analyst.md."""
from backend.maf.agents.policy import AgentPolicy

POLICY = AgentPolicy("Document analyst", "Ranks and answers from retrieved requirement-document chunks, with checked citations", "low", max_tokens=4_000)
