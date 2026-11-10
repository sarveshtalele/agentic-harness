"""Long multi-step project work on MAF's own harness (todos, modes, memory, skills). Built by maf/harness.py.

Prompt: prompts/harness.md. Evals: evals/harness.json.
"""
from backend.maf.agents.policy import CHAT_READ, AgentPolicy

# Tools MAF's harness providers add themselves (TodoProvider, AgentModeProvider, FileMemoryProvider). Listed so the
# audit does not log them as refused; they never reach repository code or platform state.
HARNESS_PROVIDER_TOOLS = frozenset({
    "todos_add", "todos_complete", "todos_get_all", "todos_get_remaining", "todos_remove", "mode_get", "mode_set",
    "file_memory_delete", "file_memory_grep", "file_memory_ls", "file_memory_read", "file_memory_replace",
    "file_memory_replace_lines", "file_memory_write",
})

POLICY = AgentPolicy(
    "Project harness",
    "Plans and works through multi-step project tasks with todos, modes, memory, and skills",
    "high",  # runs the repository's own tests in its sandbox copy
    chat_tools=frozenset(CHAT_READ | {"save_document", "project_status", "list_findings", "verify_ledger", "start_workflow",
                                      "run_tests", "scan_repository", "sandbox_status"} | HARNESS_PROVIDER_TOOLS),
)
