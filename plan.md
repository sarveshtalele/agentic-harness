# Plan

> The active plan is `docs/MASTER_PLAN.md` (2026-11-10). This file keeps the history of earlier phases.

Modify the existing project into a production-ready app for BAs and developers, on branch `feat/real-maf-platform`. Nothing is deleted without the owner's permission. The previous code stays in Git history at commit 09f14fe. The `legacy/` folder was removed in commit f1a7070.

## Audit of the previous code

| Problem | Evidence (paths at commit 09f14fe) | Resolution |
|---|---|---|
| "MAF" was hand-written, and the real package was not installed | `src/backend/maf/core.py`, `requirements.txt` | Real `agent-framework` packages |
| Engine had a dead code path calling a missing method | `maf/core.py` `step` calls `should_route` | Replaced by MAF workflows |
| Simulated PRs, tokens, and connection success | `github/client.py`, `routes_agentic_qe.py` (`ghp_simulated`, `simulated: True`, latency 34/68/82) | Real calls only |
| Tautological tests reported as verified | `routes_agentic_qe.py` copilot `/test`, `qe/scanner.py` `assert True` | Refused by checks |
| Canned requirements when none exist | `maf/agents/qe.py` `_create_strategy` | Error instead |
| Findings with hardcoded sample code | `qe/scanner.py` | Ruff and quote-verified review |
| Hardcoded proxy URL, model, and default repo | `llm/client.py`, `app/page.tsx` | Settings and environment |
| Token placed in clone URL and plaintext settings | `routes_agentic_qe.py`, `data/settings.json` | Encrypted, env-scoped header |
| Project picked from a header dropdown; one 1021-line page | `components/Header.tsx`, `app/page.tsx` | Projects page and routes |
| Bash and PowerShell scripts in parallel | `scripts/` | `scripts/dev.py` |

## Feature parity with the previous app

| Previous feature | New location | Status |
|---|---|---|
| Repository Hub: token, URL, `owner/repo`, local path | Repository page, Settings | Ported |
| BA Studio: BRD and PRD, review, refine, Gherkin, versions, exports | BA Studio, document page | Ported |
| Feature Builder and error chat, PR, merge, ZIP | Feature Builder, Bug Scan, run panel | Ported |
| Bug Diagnostic with fixes | Bug Scan | Ported |
| QE Test Studio | QE Studio | Ported |
| HITL Governance with manual decisions | Governance | Ported |
| Observability and agent evaluations | Runs & Metrics, Prompts | Ported; numbers now come from real runs |
| Copilot with `/scan`, `/fix`, `/test`, `/verify`, `/gates` | Copilot | Ported as agent tools |
| XLSX and PPTX source upload | BA Studio | Ported |

## Phases

| # | Phase | Result |
|---|---|---|
| 1 | Review code, plugin, and MAF docs | Audit above, `docs/ARCHITECTURE.md` |
| 2 | Guardrails and tracking | `CLAUDE.md`, `.claude/settings.json`, `progress.md` |
| 3 | Backend on real MAF | `src/backend` |
| 4 | Parity and plugin rule alignment | Table above |
| 5 | UI: projects page first | `src/frontend`, `Design.md` |
| 6 | Chatbot on AG-UI and CopilotKit | `/agui`, `components/Chat.tsx` |
| 7 | Tests and evidence | `tests/`, `docs/evidence/` |
| 8 | Final guide | `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`, `README.md` |
| 9 | Agent governance: policy, guardrails, evals, observability | `maf/governance.py`, `maf/evals.py`, `/agents` |
| 10 | Sign-in, per-user allocations, confidence review beside each stage | `core/auth.py`, `api/auth.py`, `core/doc_checks.py`, `/login`, `/users` |
| 11 | Master specification: Skill Studio, Progressive Disclosure, MAF 2.0 conformance | `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md` |
| 15 | Delivery phase 6: deterministic metrics, RAGAS evaluator, benchmarks, stored scores, score cards | `maf/evals/`, `evals/benchmarks/`, `docs/EVALUATIONS.md` | Built |
| 14 | Delivery phase 5: per-case confidence, code-computed verdicts, gate reopening, signature checks, setup and data stages, defect records, case budget, `qa-execution-engineer` | `qe/confidence.py`, `qe/emit.py`, `qe/test_data.py` | Built |
| 13 | Delivery phase 4: plugin skills injected into workflows, chat skill selection, and a live tool check per model | `skills/`, `core/skills.py`, `maf/skill_chat.py`, `llm.tool_check` | Built |
| 12 | Delivery phases 1 to 3: names and integrity, typed errors and logs, models, limits, and roles | `core/models.py`, `core/errors.py`, `core/logs.py`, `core/auth.py`, `api/settings.py`, `maf/engine.py`. Built. Phase 4, Skills, is next |

Latest results, after phase 6: offline 447 passed, end-to-end 32 of 33 passed (`test_f4` failed, as Feature Builder ended with a failing verdict), agent evaluations 33 of 33 passed. The finance repository QE run executed 56 tests, 14 passed and 42 failed, coverage 53%, verdict FAIL, 446,876 tokens. Results vary widely between runs.

## How MAF is used

See `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`. In short: `Agent` for specialists, structured edits applied by guarded code for feature and fix work, `WorkflowBuilder` with `request_info` and checkpoints for gates, fan-out and fan-in for scans, context providers for memory, middleware for tool audit, `AgentFrameworkAgent` for AG-UI, and `evaluate_agent` for prompt quality.

## Documentation sources

The MAF PDF and the installed package source are primary. Context7 and Firecrawl supplied CopilotKit and AG-UI setup details. `.mcp.json` registers both for future sessions. `npx rea-agents setup` was run for Claude Code. REA reverse engineers compiled apps, so this source-based project did not need it.

## Decisions needing the owner

| Item | Default until told otherwise |
|---|---|
| Commit and push | Not done |
| Old `data/sdlc.sqlite3` and `workspaces/` | Left untouched and not migrated |

## Modular architecture (owner request, 2026-11-01)

The backend grew two large files: `app.py` (833 lines) and `maf/workflows.py` (790 lines). Both split along feature lines. Public imports stay the same so callers and tests do not change.

```text
src/backend/
  app.py                 App creation, middleware, router includes only
  api/                   One router per area: projects, repositories, documents, runs, chat, governance, settings
  maf/
    agents/              runtime.py (AgentCall, build) and one file per agent holding its policy
    tools/               One file per tool, assembled by repo_tools, document_tools, chat_tools
    workflows/           shared.py, edits.py, then ba.py, bug_scan.py, change.py, qe.py. Adding a workflow means adding a file
    engine.py, governance.py, evals.py, agui.py, llm.py
```

### Harness patterns chosen

Source: Harness Patterns (ashishpatel26.github.io/agent-harness-engineering-pattern), 192 patterns. Most are general catalog entries, so only the ones that fix a real gap here are adopted.

| Pattern | Status | Where |
|---|---|---|
| Layered architecture, Registry (8.04, 2.06) | Adopting | Router, workflow, agent, and tool files with registries |
| Plugin discovery (2.07) | Adopting | Agent files found by scanning the package |
| Backpressure and Bulkhead (3.10, 7.05) | Adopting | A process-wide limit on concurrent model calls, needed on a one-core plan |
| Cut-off reply guard (1.01) | Adopting | A reply stopped by the token limit is reported as cut off |
| Retry with backoff (3.04) | Have | OpenAI SDK retry plus `ATLAS_MODEL_TIMEOUT` |
| Structured output with repair (3.16) | Have | `AgentCall.typed` |
| Middleware, Proxy (1.05, 2.14) | Have | `governance.telemetry`, `tool_audit`, `governance.allowed` |
| Append-only log, Immutable records (7.09, 4.13) | Have | `core/ledger.py`, document versions |
| Checkpoint and resume (1.07) | Have | `FileCheckpointStorage` in `engine.py` |
| Health check (7.08) | Have | `/api/health`, wired to App Service Health check |
| One-door gateway (8.11) | Have | `session_guard` denies every API path by default, and Azure adds an access restriction on the backend |
| Scripted stand-in tests (12.04) | Have | `tests/scripted_client.py` |

Skipped: circuit breaker, fallback chain, semantic cache, sharding, CQRS, tenant rate limits, durable execution engines, and CodeAct. Agentic QE Platform runs on one instance with one model, and sandboxes do not isolate untrusted users yet, so none of these fixes a problem it has. Add them when it serves several tenants or models.

### Azure target

Two Linux web apps on one B1 plan in East US: ₹1.6189 per hour, ₹1,181.80 per 730-hour month, from the Azure Retail Prices API on 2026-11-01. It is the cheapest region checked and the closest to the current model endpoint. Central India is ₹1,251.29. Free F1 costs ₹0 but allows 60 CPU minutes a day and has no Always On, so workflows would die. Microsoft documents that the Kudu ZIP drag-and-drop page does not work on Linux, so the guide uses Cloud Shell upload, with Kudu file upload as the alternative. SQLite on the `/home` network share cannot use WAL, so the journal mode becomes a setting.

## Observability design (owner request, 2026-11-01)

The page reads existing stores, with one new table.

| Log type | Source |
|---|---|
| Skill | `run_events` stage starts, mapped to the agentic-qe skill each stage implements |
| Agent | `agent_calls` |
| Tool, MCP tool | New `tool_calls` table, written by `tool_audit` for workflows and chat |
| Workflow step, approval | `run_events` |
| Guardrail | `guardrail_events` |
| Audit | Hash-chained `ledger` |

Agentic QE Platform connects to no MCP server, so the MCP count is zero and the page says that. The `kind` column is there for when one is added.

## MAF harness rebuild (owner request, 2026-11-10). Awaiting approval

Full plan, mappings, and phase table: `docs/HARNESS_REBUILD_PLAN.md`. In short: the chat "harness" in `src/backend/harness/` does not use MAF and holds most of the fabricated data. MAF 1.24 ships `create_harness_agent` (todos, modes, compaction, file memory, skills, tool approval, background agents, looping), so the rebuild composes that and keeps the old engine behind `ATLAS_HARNESS_ENGINE=legacy` until the new one passes. Nothing is deleted.

Revision 2 (2026-11-10): the plugin format follows the owner's skills marketplace (`SKILL.md` + `marketplace.yaml`); Skill Studio runs the marketplace `skill-creator` 10-phase lifecycle with the task-list approval enforced in code; security scanning uses the real NVIDIA SkillSpector; plugins and profiles follow DeepSeek Harness; desktop is Electron if approved; Rieseberg's altitude, depth, and range become four CI-checked targets. See `docs/HARNESS_REBUILD_PLAN.md`.

## Tracing (H9, 2026-11-11)

OpenTelemetry through MAF's instrumentation plus platform spans, a local `spans` table (migration 020) with retention, optional OTLP, and a trace explorer at `/traces` with server-side access rules. See `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md` section 2.8.

## Harness execution world and the agentic-qe plugin (H2, H3, 2026-11-11)

- Workspace per project and thread: the project's sandbox clone (`repos.sandbox.initialize_sandbox`, refused without a repository) plus `data/harness/<project>/scratch/<thread>/` as the shell's TMPDIR.
- MAF `FileAccessProvider` on a `FileSystemAgentFileStore` subclass rooted at the clone (reads auto-approved, writes approved, `.git/` refused, every path also through `safe_path`).
- MAF shell: `agent_framework_tools.shell.LocalShellTool` (package `agent-framework-tools==1.0.0b261030`, released with core 1.24.0), its `run` replaced by an argument-list runner (`repos.sandbox.execute_command`, no shell) with the allowlist `node npx npm python python3 pytest git` (git read-only verbs), `clean_sandbox_env()`, `ATLAS_HARNESS_SHELL_TIMEOUT`, an approval card per command and a ledger row per command.
- Web profile: each shell or write call takes one of `ATLAS_MAX_SANDBOXES` lease rows (migration 021); a sixth is refused naming the queue.
- Plugin `agentic-qe` replaced by the upstream plugin at `8a7497b` (D4), `plugins/agentic-qe/PINNED`.
- Claude Code hook adapter (`core/plugin_hooks.py`) runs `hooks/hooks.json` commands as argument lists with `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PROJECT_DIR`, the hook JSON on stdin, the hook timeout and `clean_env`: PreToolUse/PostToolUse around write and shell (MAF function middleware), UserPromptSubmit and SessionStart in `maf/agui.py`, SubagentStop after a plugin agent's run.
- Plugin `agents/*.md` become MAF background agents with read-only workspace tools (MAF background agents have no approval channel, so Write/Edit/Bash are not given to them).

## Phase Q1: QE workflow correctness (2026-11-11)

Bugs B1 to B7 and B14 to B18 of `docs/analysis/2026-11-11-markdown-html-converter-trace.md`, in the QE workflow files only (`docs/MASTER_PLAN.md` Phase Q). An empty repository stops before Gate 0 unless the run asks for `spec_first`; Exception cases only for stated error behaviour; test data and datasets follow the requirement's input type; a test that defines or stubs its subject is refused; a verdict without a real execution is INCONCLUSIVE; real reasons for REJECT decisions; G3 to G5 approve their documents; event data redacted. Tests: `tests/test_qe_correctness.py`. Q2 to Q4 wait for H2 and H3.

## Landing page (owner request, 2026-11-11)

`/` becomes a public landing page: what the platform does, the desktop downloads for macOS and Windows (from `ATLAS_DOWNLOADS_URL` through `app/api/downloads`, empty state when none are published), and a Sign in button. A signed-in visitor sees "Open workspace" instead. The projects list moves to `/projects`, and sign-in lands there. `AuthGate` treats `/` like `/login` (no session needed); the landing page reads no project data, and every API path stays denied by default.

## Plugin command focus (owner request, 2026-11-11: "run the complete workflow")

The live agentic-qe cycle stopped at Gate 1 because the model never wrote `02-requirements/requirements.json` (622 tool calls, 322 reads, no write). Causes found in `docs/evidence/runs/2026-11-11-harness-plugin/transcript.jsonl`:
1. The command's instructions lived only in a user message, and MAF compaction summarised it away mid-turn, so the model forgot which command it was running ("Let me start the QE workflow as the user requested").
2. The platform's own QE tools (`start_workflow`, `project_status` gates, platform documents, the repository copy) stayed visible beside the plugin's, so the model mixed the two gate systems and read every file twice.
3. Nothing told the model which files the step must produce, and the command's "wait for the user's yes" read as "ask in chat", so it explored until the tool budget ran out.

Fix (`maf/harness_kit/active_command.py`):
- A slash command becomes the thread's **active command**, kept beside the thread and given to the model in the instructions on every call (MAF `ContextProvider`), never compacted. The chat history keeps only what the user typed.
- While a plugin command is active, the platform's QE, document and repository tools are hidden; the model works only on the workspace (MAF file access, the shell) with the plugin's hooks.
- The instructions list the files the command may create (`Paths this command may create`, `<app-name>` filled in), each marked written or missing on disk, and say that the approval card on each write is the yes the command asks for.

## Phase 2 (owner request, 2026-11-12), awaiting approval

See `docs/FINAL_PLAN.md` section 14: a live capability index for the harness, then a home page with gated downloads, a governance page for features, BA Studio uploads and a brainstorming workflow, Confluence import through MCP, the QE cycle traced end to end, and admin-issued desktop credentials.
