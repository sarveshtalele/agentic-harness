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

from backend import config
from backend.config import DATA_DIR, HARNESS_CONTEXT_TOKENS, HARNESS_MAX_ROUNDS, HARNESS_MAX_TOOL_CALLS
from backend.core import auth, plugin_grants, plugins, prompts
from backend.core.mcp import mcp_tools_for
from backend.core.mcp.harness import refresh_stale
from backend.maf import governance, llm, tools
from backend.maf.harness_kit import active_command, plugin_agents, specialists, verify, workspace
from backend.maf.harness_kit.budget import turn_budget
from backend.maf.harness_kit.errors import error_shape
from backend.maf.harness_kit.tool_hygiene import tool_hygiene
from backend.maf.harness_kit.hook_middleware import guarded
from backend.maf.harness_kit.shell import ShellProvider, WorkspaceShell
from backend.maf.harness_kit.shell_tools import ShellToolsProvider
from backend.maf.harness_kit.bg_tasks import BackgroundProvider
from backend.maf.harness_kit.plugin_contract import PluginContractProvider
from backend.maf.harness_kit import checkpoints, os_sandbox, permissions, skill_scopes
from backend.maf.harness_kit.skill_runner import SkillHealthProvider, runner as skill_runner, skill_dirs  # noqa: F401
from backend.core.script_runtime import SCRIPT_EXTENSIONS
from backend.maf.harness_kit.strict_args import strict_arguments
from backend.maf.harness_kit.unknown_tools import unknown_tool_hints
from backend.maf.harness_kit.write_first import write_first
from backend.maf.harness_kit.nudges import while_working
from backend.maf.harness_kit.stop_hooks import with_stop_hooks
from backend.maf.harness_kit.catalog import CORE, RISKY, Catalogue, LoadedTools
from backend.maf.harness_kit.snapshots import APPROVALS, SNAPSHOTS, scope, session_id  # noqa: F401 - used by maf/agui.py and api/chat.py
from backend.maf.runtime import ProjectContext, tool_audit
from backend.maf.tools import find_tools, load_tools

AGENT = "harness"
HARNESS_DIR = DATA_DIR / "harness"
STUDIO_ONLY = frozenset({"skill-creator"})  # Skill Studio's model instructions; the harness uses create_skill


def _skills(ws=None) -> SkillsProvider:
    """Skills from every discovered plugin (plus skills/ as local-skills), read fresh each turn so a new plugin folder
    shows up without a restart. Command skills (disable-model-invocation: true, like agentic-qe's qe-*) are user
    commands, so the model never sees them. Platform skills are trusted content: reading one needs no pause. Running a
    skill's `scripts/run.py` waits for the human's approval card (`harness_kit/skill_runner.py`).

    A plugin granted to other roles (core/plugin_grants.py) is left out for this user, so its skills never reach the model.
    """
    # personal, then repository, then plugin and platform skills: the first skill of a name wins (Claude Code's precedence)
    paths = skill_scopes.ordered(ws.root if ws else None, plugins.skill_paths(role=plugin_grants.role_of(auth.current_user.get())))
    commands = set().union(*(plugins.command_skill_names(path) for path in paths))
    hidden = commands | STUDIO_ONLY  # one way per job: skills are made with the create_skill tool, not the Studio's own instructions
    # every common script language is discovered; the runner picks the interpreter and refuses flagged scripts (step 3)
    files = FileSkillsSource(paths, script_runner=skill_runner(ws), script_extensions=SCRIPT_EXTENSIONS)
    source = DeduplicatingSkillsSource(FilteringSkillsSource(files, lambda skill, _ctx: skill.frontmatter.name not in hidden))
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
        ToolResultCompactionStrategy(keep_last_tool_call_groups=10), SummarizationStrategy(client=summarizer, target_count=8)])  # keep recent reads (FINAL_PLAN 5.4)


def build(project_id: str, thread_id: str, start_run, *, user_id: str | None = None, model: str = "") -> Agent:
    """A harness agent for one chat turn. Same checks as `runtime.build`, then MAF's batteries-included harness."""
    governance.require_enabled(AGENT)
    user_id = user_id or auth.acting_user(project_id)
    model = auth.model_for(project_id, AGENT, None, user_id, model)
    auth.check_allowance(project_id, user_id, model)
    every = governance.allowed(AGENT, tools.repo_tools(project_id) + tools.document_tools(project_id) + tools.chat_tools(project_id, thread_id, start_run) + tools.harness_tools(project_id, thread_id, start_run), True)
    dirs = state_dirs(project_id, user_id)
    ws = workspace.open_workspace(project_id, thread_id, user_id)  # None without a repository: no write or shell tools then
    command = active_command.current(dirs["tools"], thread_id)
    if ws:  # one way to read files: MAF's file tools on the workspace, where edits land (the platform's read the ingested copy)
        every = [t for t in every if t.name not in ("list_files", "read_file", "grep")]
    if command and ws:  # a plugin command does the QE work itself: one way per job, so the platform's QE and repository tools step aside
        every = [t for t in every if t.name not in active_command.PLATFORM_QE_TOOLS]
    for tool in every:
        if tool.name in RISKY:
            tool.approval_mode = "always_require"  # these objects are built for this turn, so other agents keep theirs
    user = auth.current_user.get()
    if user:
        refresh_stale()  # background: tool lists older than 10 minutes are listed again for the next turn
    catalogue = Catalogue([t for t in every if t.name not in CORE], mcp_tools_for(project_id, user) if user else [])
    loaded = LoadedTools(dirs["tools"], project_id, thread_id, catalogue)
    core = [t for t in every if t.name in CORE] + [find_tools.build(catalogue), load_tools.build(catalogue, loaded)]
    ref, max_output = prompts.ref(AGENT), governance.token_limit(AGENT)
    telemetry = governance.telemetry(AGENT, project_id, None, "chat", model, user_id, ref, json.dumps([]), also_allowed=frozenset(catalogue.mcp))
    client = llm.client(model, max_rounds=HARNESS_MAX_ROUNDS, max_tool_calls=HARNESS_MAX_TOOL_CALLS, detailed_errors=True)
    compaction = _compaction(client, model, HARNESS_CONTEXT_TOKENS - max_output, telemetry)
    keep_going, next_message = with_stop_hooks(ws, while_working(todos_remaining(looping_modes=["execute"])), todos_remaining_message)
    mode, rules = permissions.get_mode(dirs["tools"], thread_id), permissions.load_rules(ws.root if ws else None)  # once per turn
    sandbox = {"network": os_sandbox.settings(ws.root)["network"]} if ws and os_sandbox.active(mode, ws.root) else None
    world, providers = _world(ws, sandbox)
    providers.append(SkillHealthProvider(skill_scopes.ordered(ws.root if ws else None, plugins.skill_paths(role=plugin_grants.role_of(auth.current_user.get()))),
                                         note=skill_scopes.note(ws.root if ws else None)))
    if command:  # without a repository it still says which command runs; WorkspaceContext says there are no file tools
        providers.append(active_command.ActiveCommandContext(command, ws.root if ws else None, thread_id))
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
        skills_provider=_skills(ws),
        # like Claude Code and Codex the harness does the work; risky tools still stop for an approval card. /plan switches mode
        mode_provider=AgentModeProvider(default_mode="execute"),
        background_agents=specialists.build(project_id, user_id) + plugin_agents.build(project_id, user_id, model, ws, mode, rules) or None,
        # in execute mode MAF re-runs the turn while todos stay open; a pending approval always stops it
        loop_should_continue=keep_going,  # open todos, then the Stop hooks (stop_hooks.py)
        loop_next_message=next_message,
        loop_max_iterations=HARNESS_MAX_ROUNDS,
        disable_web_search=True,  # no data leaves through a hosted search tool
        context_providers=[ProjectContext(project_id, full=True), loaded, workspace.WorkspaceContext(ws), *providers],
        auto_approval_rules=[permissions.approval_rule(lambda: mode, lambda: rules, sandbox is not None)],  # allow and deny skip the card
        middleware=[permissions.enforce(lambda: mode, lambda: rules, sandbox is not None), strict_arguments, unknown_tool_hints(catalogue, loaded), write_first(thread_id, ws.root if ws else None, command), *([verify.verifier(ws, command)] if ws and command else []),
                    turn_budget(thread_id, resume=f"/{command['name']} {command['args']}".rstrip() if command else "continue"), tool_hygiene(), error_shape(), tool_audit(AGENT, project_id, None, "chat"), *([guarded(ws), checkpoints.checkpoint(ws, checkpoints.folder(dirs["tools"], thread_id), checkpoints.new_turn())] if ws else []),
                    telemetry],
        **world,
    )


def _world(ws, sandbox: dict | None = None) -> tuple[dict, list]:
    """Plan H2: MAF file access on the workspace (reads free, writes approved) and MAF's shell tool confined to it."""
    if ws is None:
        return {}, []
    world = {"file_access_store": workspace.WorkspaceStore(ws.root), "file_access_disable_readonly_tool_approval": True}
    if config.PROFILE == "web":  # D-SHELL-WEB: the shared server keeps the allowlisted runner
        return world, [ShellProvider(WorkspaceShell(ws))]  # the shell comes through a provider: see harness_kit/shell.py
    return world, [ShellToolsProvider(ws, sandbox), BackgroundProvider(ws.thread_id), PluginContractProvider(ws)]  # real shells (D-SHELL); plugin contracts (R5)
