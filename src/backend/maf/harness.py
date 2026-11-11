"""The project harness: MAF's own `create_harness_agent`, wired into the platform's governance (plans P2 and M4).

MAF supplies the loop, todos, plan/execute modes, file memory, skills with progressive disclosure, background agents,
tool approval, compaction, and per-call history. The platform adds what every agent gets in `runtime.build`: the enabled
check, the model allowance, deny-by-default tools, `tool_audit`, telemetry, and the project context, plus progressive tool
discovery (`harness_kit/catalog.py`), the governed specialists as background agents (`harness_kit/specialists.py`) and
durable AG-UI thread snapshots (`harness_kit/snapshots.py`). State lives under `data/harness/` (never the process cwd),
keyed by project, user, and chat thread.
"""
from __future__ import annotations

import json

from agent_framework import (
    AgentModeProvider,
    Agent,
    CharacterEstimatorTokenizer,
    DeduplicatingSkillsSource,
    FileHistoryProvider,
    FileSkillsSource,
    FileSystemAgentFileStore,
    FilteringSkillsSource,
    SkillsProvider,
    SummarizationStrategy,
    TodoFileStore,
    TodoProvider,
    TokenBudgetComposedStrategy,
    ToolResultCompactionStrategy,
    create_harness_agent,
    todos_remaining,
    todos_remaining_message,
)

from backend.config import DATA_DIR, HARNESS_CONTEXT_TOKENS, HARNESS_MAX_ROUNDS, HARNESS_MAX_TOOL_CALLS
from backend.core import auth, plugin_grants, plugins, prompts
from backend.core.mcp import mcp_tools_for
from backend.maf import governance, llm, tools
from backend.maf.harness_kit import plugin_agents, specialists, workspace
from backend.maf.harness_kit.hook_middleware import guarded
from backend.maf.harness_kit.shell import ShellProvider, WorkspaceShell
from backend.maf.harness_kit.nudges import while_working
from backend.maf.harness_kit.catalog import CORE, RISKY, Catalogue, LoadedTools
from backend.maf.harness_kit.snapshots import APPROVALS, SNAPSHOTS, scope, session_id  # noqa: F401 - used by maf/agui.py and api/chat.py
from backend.maf.runtime import ProjectContext, tool_audit
from backend.maf.tools import find_tools, load_tools

AGENT = "harness"
HARNESS_DIR = DATA_DIR / "harness"
STUDIO_ONLY = frozenset({"skill-creator"})  # Skill Studio's model instructions; the harness uses create_skill


def _skills() -> SkillsProvider:
    """Skills from every discovered plugin (plus skills/ as local-skills), read fresh each turn so a new plugin folder
    shows up without a restart. Command skills (disable-model-invocation: true, like agentic-qe's qe-*) are user
    commands, so the model never sees them. Platform skills are trusted content: reading one needs no pause, and there
    is no script runner yet.

    A plugin granted to other roles (core/plugin_grants.py) is left out for this user, so its skills never reach the model.
    """
    paths = plugins.skill_paths(role=plugin_grants.role_of(auth.current_user.get()))
    commands = set().union(*(plugins.command_skill_names(path) for path in paths))
    hidden = commands | STUDIO_ONLY  # one way per job: skills are made with the create_skill tool, not the Studio's own instructions
    source = DeduplicatingSkillsSource(FilteringSkillsSource(FileSkillsSource(paths), lambda skill, _ctx: skill.frontmatter.name not in hidden))
    return SkillsProvider(source, disable_load_skill_approval=True, disable_read_skill_resource_approval=True)


def state_dirs(project_id: str, user_id: str) -> dict:
    """Where this user's harness state for this project lives. Ids are platform ids, never user input."""
    base = HARNESS_DIR / project_id
    dirs = {"todos": base / "todos", "memory": base / "memory" / user_id, "history": base / "history", "tools": base / "tools"}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _compaction(client, model: str, budget: int, telemetry) -> TokenBudgetComposedStrategy:
    """MAF compaction inside the context budget: collapse older tool results first, then summarize the oldest turns."""
    summarizer = llm.client(model)
    if summarizer is not client:  # a fresh client per call in production; the summary round is recorded like any other
        summarizer.chat_middleware.append(telemetry)
    return TokenBudgetComposedStrategy(token_budget=budget, tokenizer=CharacterEstimatorTokenizer(), strategies=[
        ToolResultCompactionStrategy(keep_last_tool_call_groups=4), SummarizationStrategy(client=summarizer, target_count=8)])


def build(project_id: str, thread_id: str, start_run, *, user_id: str | None = None, model: str = "") -> Agent:
    """A harness agent for one chat turn. Same checks as `runtime.build`, then MAF's batteries-included harness."""
    governance.require_enabled(AGENT)
    user_id = user_id or auth.acting_user(project_id)
    model = auth.model_for(project_id, AGENT, None, user_id, model)
    auth.check_allowance(project_id, user_id, model)
    every = governance.allowed(AGENT, tools.repo_tools(project_id) + tools.document_tools(project_id) + tools.chat_tools(project_id, thread_id, start_run) + tools.harness_tools(project_id, thread_id, start_run), True)
    for tool in every:
        if tool.name in RISKY:
            tool.approval_mode = "always_require"  # these objects are built for this turn, so other agents keep theirs
    user = auth.current_user.get()
    catalogue = Catalogue([t for t in every if t.name not in CORE], mcp_tools_for(project_id, user) if user else [])
    dirs = state_dirs(project_id, user_id)
    loaded = LoadedTools(dirs["tools"], project_id, thread_id, catalogue)
    core = [t for t in every if t.name in CORE] + [find_tools.build(catalogue), load_tools.build(catalogue, loaded)]
    ref, max_output = prompts.ref(AGENT), governance.token_limit(AGENT)
    telemetry = governance.telemetry(AGENT, project_id, None, "chat", model, user_id, ref, json.dumps([]), also_allowed=frozenset(catalogue.mcp))
    client = llm.client(model, max_rounds=HARNESS_MAX_ROUNDS, max_tool_calls=HARNESS_MAX_TOOL_CALLS)
    compaction = _compaction(client, model, HARNESS_CONTEXT_TOKENS - max_output, telemetry)
    ws = workspace.open_workspace(project_id, thread_id, user_id)  # None without a repository: no write or shell tools then
    world, providers = _world(ws)
    return create_harness_agent(
        client,
        name=AGENT,
        agent_instructions=prompts.active(AGENT)["body"],
        tools=core,
        max_context_window_tokens=HARNESS_CONTEXT_TOKENS,
        max_output_tokens=max_output,
        before_compaction_strategy=compaction,  # per model call
        after_compaction_strategy=compaction,  # the stored session history after the turn
        history_provider=FileHistoryProvider(dirs["history"], load_messages=False),  # AG-UI sends the thread; this keeps what the model saw
        todo_provider=TodoProvider(store=TodoFileStore(dirs["todos"])),
        file_memory_store=FileSystemAgentFileStore(dirs["memory"]),
        skills_provider=_skills(),
        # like Claude Code and Codex the harness does the work; risky tools still stop for an approval card. /plan switches mode
        mode_provider=AgentModeProvider(default_mode="execute"),
        background_agents=specialists.build(project_id, user_id) + plugin_agents.build(project_id, user_id, model, ws) or None,
        # in execute mode MAF re-runs the turn while todos stay open; a pending approval always stops it
        loop_should_continue=while_working(todos_remaining(looping_modes=["execute"])),
        loop_next_message=todos_remaining_message,
        loop_max_iterations=HARNESS_MAX_ROUNDS,
        disable_web_search=True,  # no data leaves through a hosted search tool
        context_providers=[ProjectContext(project_id, full=True), loaded, workspace.WorkspaceContext(ws), *providers],
        middleware=[tool_audit(AGENT, project_id, None, "chat"), *([guarded(ws)] if ws else []), telemetry],
        **world,
    )


def _world(ws) -> tuple[dict, list]:
    """Plan H2: MAF file access on the workspace (reads free, writes approved) and MAF's shell tool confined to it."""
    if ws is None:
        return {}, []
    world = {"file_access_store": workspace.WorkspaceStore(ws.root), "file_access_disable_readonly_tool_approval": True}
    return world, [ShellProvider(WorkspaceShell(ws))]  # the shell comes through a provider: see harness_kit/shell.py
