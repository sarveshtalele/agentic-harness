# Harness Gap Analysis: our MAF harness against DeepSeek Harness

Written 2026-11-10 from:
- the cloned `deepseek-ai/deepseek-harness` docs (`docs/architecture.md`, `docs/tool-execution-pipeline.md`, `packages/boot/plugin-manager`, `SAFETY.md`);
- the code on `feature/maf-harness-platform` at `58e23bd`;
- the live user-story run (`docs/HARNESS_USER_STORIES.md`, results in `docs/evidence/runs/`).

The **Status** column says what a command or run showed, not what the code is meant to do.

## Capability map

| Capability | DeepSeek Harness | Ours today | Status | How to close it with MAF |
|---|---|---|---|---|
| Agent loop | `core/agent-loop`, step and turn events | `create_harness_agent` function invocation | Working (live) | - |
| Plan / todos | Todo tools, session events | MAF `TodoProvider` + `TodoFileStore`, todo panel on `/harness` | Working (live, E2E `test_13b`) | - |
| Plan / execute modes | Agent presets | MAF `AgentModeProvider` | Partial: the mode resets each AG-UI request | MAF thread snapshot store (`AGUIThreadSnapshotStore`) backed by the database |
| Skills, progressive disclosure | Skills as plugin rows | MAF `SkillsProvider` over discovered plugins; command skills filtered out | Working (live: `load_skill`) | - |
| Plugins | Everything is a plugin; profiles and bundles; plugin manager enables or disables rows; changes apply without restart | `core/plugins.py` discovery + `GET /api/plugins`; rescans each turn | Partial: read-only, no enable or disable, no install | `plugins` table + admin routes (P3/P5); install from the marketplace (P6) |
| Slash commands | `ctx.commands`, run without a model turn | None (the agentic-qe `qe-*` commands are hidden from the model) | Missing | Command registry in `maf/harness`: `/plugin:cmd args` runs first, then sends the command body to the agent (P3b) |
| Sub-agents / agent teams | Subagent providers, Agent Teams with a shared task board | None in the harness; the specialists run only inside workflows | Missing | MAF `BackgroundAgentsProvider` with the existing `maf/agents` specialists, each built through `runtime.build` so governance applies (P3b) |
| Hooks | `agent/*` and `tools/*` events | `tool_audit` + telemetry middleware | Partial: the plugin's own hooks do not run | MAF `create_agent_hooks_middleware` + a Claude Code hook adapter that runs agentic-qe's Node hooks (P3b) |
| Tool pipeline with permission | pre-execute → guards → approval → execute → post | Policy allowlist, audit, telemetry; MAF `ToolApprovalMiddleware` is on but the chat UI cannot answer an approval | Partial | Render AG-UI approval requests in `Chat.tsx` (CopilotKit HITL), then put `run_tests` and future write tools behind approval |
| Sandbox | `ctx.sandbox` backend; fs and subprocess share one execution world | `run_tests` in a git sandbox clone; workflows in worktrees; `clean_env`, timeout | Working for tests; no shell | Keep without a shell locally. On Azure, run sandbox jobs as Container Apps Jobs (below) |
| File access | `ctx.fs` providers and `fs/*` events | Read-only repository tools through `safe_path`; edits only through workflows | By design | MAF `FileAccessProvider` (read-only) when needed |
| MCP | Plugin rows | MCP page returns 501; no client connection | Missing | `MCPStdioTool` (desktop) / `MCPStreamableHTTPTool` (Azure) per plugin `mcp.json` (P4) |
| Sessions and history | Append-only session log; "model-visible means logged"; fork at a turn | `FileHistoryProvider` per project, chat messages in SQLite, `agent_calls` and `tool_calls` rows | Partial: no fork, no replay check | CI gate 2 replay test; fork means copying the history file to a new thread |
| Context compaction | Session projections | Sliding window, 30 groups | Basic | `ContextWindowCompactionStrategy` once the model's window is recorded in `core/models.py` |
| Skill creation in chat | - | Skill Creator Studio pages only; no harness tool | Missing (HS-10) | `create_skill` tool that drafts to `data/skill-drafts/` and needs the user's approval (P6) |
| Skill evaluation | Benchmarks | Studio `evaluate` endpoint; see the live HS-09 result | See evidence | evaluator plugin + NVIDIA SkillSpector (P6) |
| Observability | Telemetry plugin | `agent_calls`, `tool_calls`, ledger, observability page | Working | OpenTelemetry exporter to Application Insights on Azure |
| Desktop app | Electron app + private desktop host running the same web app | None | Missing | Electron shell (P9; see `docs/AZURE_DEPLOYMENT_GUIDE.md`) |
| Headless / SDK | `headless`, `sdk` profiles | `bin/harness` CLI (legacy engine) | Partial | A CLI that drives `/agui/harness` |
| Safety statement | `SAFETY.md` | `CLAUDE.md` security rules, sign-in, deny-by-default routes | Working | Add a `SAFETY.md` for operators |

## Order to make it a working professional harness

1. **P3b, the biggest functional gap:**
   - commands;
   - sub-agents through `BackgroundAgentsProvider`;
   - the Claude Code hook adapter;
   - chat approval UI.

   With these, the agentic-qe plugin runs fully inside the harness (HS-06, HS-11).
2. **P4:** real MCP.
3. **P5:** admin grants for plugins, skills and MCP (HS-12).
4. **P6:** harness `create_skill` and evaluation with SkillSpector (HS-10, HS-09).
5. **Mode persistence and compaction tuning:** thread snapshot store, model context windows.
6. **Azure and desktop:** see `docs/AZURE_DEPLOYMENT_GUIDE.md`.
