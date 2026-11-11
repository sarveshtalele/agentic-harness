"""Long multi-step project work on MAF's own harness (todos, modes, memory, skills). Built by maf/harness.py.

Prompt: prompts/harness.md. Evals: evals/harness.json.
"""
from backend.maf.agents.policy import CHAT_READ, AgentPolicy

# Tools MAF's harness providers add themselves (TodoProvider, AgentModeProvider, FileMemoryProvider, BackgroundAgentsProvider). Listed so the
# audit does not log them as refused; they never reach repository code or platform state.
HARNESS_PROVIDER_TOOLS = frozenset({
    "todos_add", "todos_complete", "todos_get_all", "todos_get_remaining", "todos_remove", "mode_get", "mode_set",
    "file_memory_delete", "file_memory_grep", "file_memory_ls", "file_memory_read", "file_memory_replace",
    "file_memory_replace_lines", "file_memory_write",
    # BackgroundAgentsProvider: delegation to the governed specialists, each audited under its own agent key
    "background_agents_start_task", "background_agents_wait_for_first_completion", "background_agents_get_task_results",
    "background_agents_get_all_tasks", "background_agents_continue_task", "background_agents_clear_completed_task",
    # progressive tool discovery (maf/harness_kit/catalog.py)
    "find_tools", "load_tools",
    # plan H2: MAF file access on the workspace (writes approved) and the allowlisted shell (each command approved)
    "file_access_read", "file_access_read_lines", "file_access_ls", "file_access_grep", "file_access_write", "file_access_delete",
    "file_access_replace", "file_access_replace_lines", "run_shell",
})

POLICY = AgentPolicy(
    "Project harness",
    "Plans and works through multi-step project tasks with todos, modes, memory, and skills",
    "high",  # runs the repository's own tests in its sandbox copy
    chat_tools=frozenset(CHAT_READ | {"save_document", "project_status", "list_findings", "verify_ledger", "start_workflow",
                                      "run_tests", "scan_repository", "sandbox_status", "create_skill"} | HARNESS_PROVIDER_TOOLS),
)
