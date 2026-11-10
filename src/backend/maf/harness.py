"""The project harness: MAF's own `create_harness_agent`, wired into the platform's governance (plan P2).

MAF supplies the loop, todos, plan/execute modes, file memory, skills with progressive disclosure, tool approval,
compaction, and per-call history. The platform adds what every agent gets in `runtime.build`: the enabled check, the
model allowance, deny-by-default tools, `tool_audit`, telemetry, and the project context. State lives under
`data/harness/` (never the process cwd), keyed by user, project, and chat thread.
"""
from __future__ import annotations

import json

from agent_framework import (
    Agent,
    FileHistoryProvider,
    FileSkillsSource,
    FileSystemAgentFileStore,
    SkillsProvider,
    SlidingWindowStrategy,
    TodoFileStore,
    TodoProvider,
    create_harness_agent,
)

from backend.config import DATA_DIR, SKILLS_DIR
from backend.core import auth, prompts
from backend.maf import governance, llm, tools
from backend.maf.runtime import ProjectContext, tool_audit

AGENT = "harness"
HARNESS_DIR = DATA_DIR / "harness"


def _skills() -> SkillsProvider:
    """Platform skills under skills/ are trusted content, so reading one needs no pause; there is no script runner yet.

    ponytail: every platform skill is offered; the per-user allowlist arrives with admin grants (plan P5).
    """
    return SkillsProvider(FileSkillsSource([SKILLS_DIR]), disable_load_skill_approval=True, disable_read_skill_resource_approval=True)


def state_dirs(project_id: str, user_id: str) -> dict:
    """Where this user's harness state for this project lives. Ids are platform ids, never user input."""
    base = HARNESS_DIR / project_id
    dirs = {"todos": base / "todos", "memory": base / "memory" / user_id, "history": base / "history"}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def build(project_id: str, thread_id: str, start_run, *, user_id: str | None = None, model: str = "") -> Agent:
    """A harness agent for one chat turn. Same checks as `runtime.build`, then MAF's batteries-included harness."""
    governance.require_enabled(AGENT)
    user_id = user_id or auth.acting_user(project_id)
    model = auth.model_for(project_id, AGENT, None, user_id, model)
    auth.check_allowance(project_id, user_id, model)
    allowed = governance.allowed(AGENT, tools.repo_tools(project_id) + tools.document_tools(project_id) + tools.chat_tools(project_id, thread_id, start_run), True)
    ref = prompts.ref(AGENT)
    dirs = state_dirs(project_id, user_id)
    return create_harness_agent(
        llm.client(model),
        name=AGENT,
        agent_instructions=prompts.active(AGENT)["body"],
        tools=allowed,
        max_output_tokens=governance.token_limit(AGENT),
        before_compaction_strategy=SlidingWindowStrategy(keep_last_groups=30),  # same window as every other platform agent
        history_provider=FileHistoryProvider(dirs["history"], load_messages=False),  # AG-UI sends the thread; this keeps what the model saw
        todo_provider=TodoProvider(store=TodoFileStore(dirs["todos"])),
        file_memory_store=FileSystemAgentFileStore(dirs["memory"]),
        skills_provider=_skills(),
        disable_web_search=True,  # no data leaves through a hosted search tool
        context_providers=[ProjectContext(project_id, full=True)],
        middleware=[tool_audit(AGENT, project_id, None, "chat"), governance.telemetry(AGENT, project_id, None, "chat", model, user_id, ref, json.dumps([]))],
    )
