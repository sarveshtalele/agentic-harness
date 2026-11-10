# MAF Harness Rebuild Plan (revision 2)

Status: **draft, waiting for the owner's approval.** Nothing in this plan has been implemented. No file has been deleted, moved, or overwritten.
Revision 1: 2026-11-10 11:07. Revision 2: 2026-11-10, after reading `shivswami/awesome-agent-skills` (marketplace branch), `deepseek-ai/deepseek-harness`, and Felix Rieseberg's "How to be more ambitious" (2026-10-13).
Branch to create after approval: `feature/maf-harness-platform`, cut from `feature/azure-kudu-deployment` at `8477250`.

This is the restart point after a context compaction. Read this file, then the newest `DECISION` rows in `PROGRESS.md`.

**What changed in revision 2**

| Area | Revision 1 | Revision 2 |
|---|---|---|
| Plugin and skill format | Own `plugin.json` | The marketplace format the owner's team already uses: `SKILL.md` + `marketplace.yaml` sidecar (validated by its `schema/marketplace.schema.json`) + `manifest.yaml` + `skill-card.json` + `evals/evals.json`. A thin `plugin.json` only groups skills, MCP servers, and agents |
| Skill Studio | 7 steps of my own | The marketplace `skill-creator` 10-phase lifecycle, run on MAF, with Phase 3 (user confirms the plan) as the hard approval gate |
| Evaluator | "Renamed AST scanner" | The marketplace `evaluator-skill` 8 weighted dimensions. Security uses the **real NVIDIA SkillSpector** CLI or MCP server. My D-17 claim that the name was invented was **wrong**: `github.com/NVIDIA/skillspector` exists (Apache-2.0). The local `skill_specter.py` is a home-grown imitation that uses NVIDIA's name, so it is replaced by the real tool, not renamed |
| Desktop | Electron or Tauri, owner picks | **Electron recommended.** DeepSeek Harness ships an Electron app that starts a private desktop host, which runs the same profile runner and web app. That is the same shape as here (Next.js + FastAPI sidecar) |
| Composition | One factory | DeepSeek's "everything is a plugin" with **profiles** (`desktop`, `azure`, `headless`) layered from the same plugin set. Each plugin registration can be undone, so disabling a plugin removes its tools, skills, and MCP servers without a restart |
| Logging principle | Ledger for state changes | Adds DeepSeek's rule **"model-visible means logged"**: every model request can be rebuilt from the session log |
| Ambition | Not considered | Section 3: altitude, depth, and range turned into concrete, checkable targets |

---

## 0. Sources and what each one gave

| Source | Reached? | What it contributed |
|---|---|---|
| `agent-framework.pdf` (968 pages) | Yes, through `pypdf` | Harness (pp. 16, 188-191), Agent Skills (228-256), Hooks (227), Looping (262), Background agents (266), Todos (270), Tool approval (281), MCP (294-303), Safety (113), FIDES (260), Observability (213) |
| Installed `agent_framework` 1.24.0, `mcp` 2.3.0 | Yes, checked with `inspect` | `create_harness_agent` plus every provider it composes (listed in Section 4.1) |
| learn.microsoft.com MAF overview (2026-10-28) | Yes | Agents, **Harness Agent**, Workflows, Integrations. "If you can write a function, do that instead of an agent" |
| `microsoft/agent-framework` `python/samples` | Yes | `01-get-started/06_agent_harness.py`, `02-agents/security`, `05-end-to-end/ag_ui_single_agent` |
| **`shivswami/awesome-agent-skills` @ `marketplace`** | Yes, `git clone` (the repo is private, so WebFetch got 404) | 24 skills in `Skills/`, the sidecar schema, the `npx … awesome-skill <id>` installer (`tools/cli/install-skill.mjs`), `skill-creator` (10 phases), `evaluator-skill` (8 dimensions, SARIF output), `skill-auditor`, `skill-gap-analyzer`, `marketplace-yaml-generator`. **Every skill's `marketplace.yaml` says `license: Proprietary (contact maintainers)`, author Tata Consultancy Services** (see decision 6) |
| **`deepseek-ai/deepseek-harness`** | Yes, `git clone` | `docs/architecture.md`, `docs/tool-execution-pipeline.md`, `packages/boot/plugin-manager`, `SAFETY.md`, `apps/desktop` + `apps/desktop-host` + `apps/web` + `apps/cli` |
| **NVIDIA SkillSpector** | Yes | `skillspector scan <dir\|zip\|git url> --format json\|sarif`, `--no-llm`, MCP server `skillspector mcp` with `scan_skill`. About 71 patterns in 17 categories. Score bands: 0-20 safe, 21-50 caution, 51-80 and 81-100 do not install |
| Felix Rieseberg, "How to be more ambitious" | Yes (pasted) | Altitude, depth, range; "use an outside judge"; the depth prompt; replace nouns with verbs; assemble the crew without role play |
| walkinglabs Lecture 01 | Yes | Five defense layers, the diagnostic loop, Definition of Done |
| ashishpatel26 Harness Patterns | Yes, first 100k of 426k characters | Pattern IDs in Section 5 |
| `sermakarevich/harness` | Yes, README | The 18-step component list |
| Firecrawl MCP, `gh` CLI | No | Invalid token; TLS failure in the sandbox. `git clone` and WebFetch were used instead |

---

## 1. Knowledge map of the existing project

| Area | Path | State |
|---|---|---|
| MAF platform | `src/backend/maf/` | **Real MAF**: `Agent`, `WorkflowBuilder`, `request_info`, checkpoints, middleware, AG-UI, `FileSkillsSource` |
| Core governance | `src/backend/core/` | Real: auth, ledger, gates, security, documents, prompts, skills, models, errors |
| QE engine | `src/backend/qe/`, `src/backend/repos/` | Real runners and static analysis. One PR "simulation" (D-16) |
| **"Harness" chat** | `src/backend/harness/` (27 files, 4,876 lines) + `api/harness.py` + `components/HarnessView.tsx` (3,126) | **No MAF.** Hand-written httpx loop, keyword routing, and hand-rolled copies of MAF primitives. Most of the dummy data is here |
| MCP | `api/mcp.py` (881), `api/mcp_playwright_tools.py` (797), `app/mcp/page.tsx` | **No MCP connection exists.** Status hardcoded `connected`; canned results |
| Skills | `skills/` (20), `plugins/agentic-qe/skills` (6), `core/skills.py`, `api/skills.py` (787), `app/skills/studio/page.tsx` (1,280) | Real MAF loading; canned studio fallback; no sidecar, no zip upload, no admin allowlist |
| Seed data | `core/seed_data.py`, from `app.py:53-56`, `cli.py:139` | **Fake projects, approved gates, and RAGAS scores on every new database** |
| Desktop | none | — |
| Azure | `deploy/azure`, `scripts/package_azure*.py`, pipelines | Packaging real; never deployed |

Baseline before any change (2026-11-10, Python 3.14, MAF 1.24.0): `pytest --ignore=tests/e2e` → **585 passed**, 0 failed, 122 s. E2E not run.

---

## 2. Goal 1: dummy data, fake results, and weak error handling

**S1** breaks a CLAUDE.md rule or governance. **S2** shows invented output as real. **S3** is weak handling.

| ID | Sev | Location | What is fake or wrong | Fix |
|---|---|---|---|---|
| D-01 | S1 | `harness/qe_tools.py:473` `run_quality_lifecycle` | `gates.decide(..., True, "qa-admin")` for G0-G5; returns 8 gates approved, scores 94-99 | Removed from the toolset. Gates stay human-only |
| D-02 | S1 | `harness/qe_tools.py:737` `security_audit` | Inserts a "passed" finding, approves G0-G5 as `security-specter`, fixed score 98 / A+, "Cloudflare" checks | Real `static_analysis.run_all` + secret scan + SkillSpector for skills. Never touches gates |
| D-03 | S1 | `qe_tools.py:541-575`, `stream_engine.py:192` | The agent can approve; signer falls back to "Agentic QE Harness"; keyword fallback emits `decide_approval(appr_test, True)` | Not an agent tool. MAF `ToolApprovalMiddleware` or workflow `request_info`, answered by a signed-in human |
| D-04 | S1 | `core/seed_data.py:15-55` | Fabricated RAGAS metrics stored as `measured` | Not called at startup. Metrics only from `maf/evals` runs |
| D-05 | S1 | `core/seed_data.py:57-342` | 4 fake projects, fake analysis, approved G0-G3, a pending gate on a nonexistent run | Not run by default. Existing rows: decision 3 |
| D-06 | S2 | `handlers/doc_handler.py:20-60`, `harness/domain_brd_generator.py` | Template BRD by topic (hardcoded ATM BRD); invented "thoughts"; all todos completed; Gate 1 approved | `/doc` runs the real `maf/workflows/ba.py` |
| D-07 | S2 | `qe_tools.py:652,673,697,724` | Fixed strategy, two hardcoded cases, a tautological vitest file written to disk, review score 96 | The real `maf/workflows/qe/*` stages and `qe/confidence.py` |
| D-08 | S2 | `qe_tools.py:161,214` | Two fixed user stories saved as a document | `business-analyst` agent + `core/gherkin.py` |
| D-09 | S2 | `qe_tools.py:450` | Fixed "SELECTOR_DRIFT" heal result | `defect-diagnostician` via the change workflow + `apply_edits` |
| D-10 | S2 | `qe_tools.py:84` | Invented routes when none are found | Empty list, and it says so |
| D-11 | S2 | `stream_engine.py:149-200` | Keyword matching invents tool calls with fake arguments | Removed. MAF function invocation decides |
| D-12 | S2 | `stream_engine.py:66` | `asyncio.sleep(0.04)` fake latency | Removed |
| D-13 | S2 | `api/mcp.py:30-370`, `harness/mcp_manager.py:31,40` | MCP "connected" without connecting | `MCPStdioTool` / `MCPStreamableHTTPTool`; status from a real `list_tools` |
| D-14 | S2 | `api/mcp.py:708-881` | Mock file content, fake writes, fixed directory listing, "420 bytes" fetch, canned success on exceptions | Calls the real MCP session; errors are errors |
| D-15 | S1 | `api/mcp.py:740-751` | `read_file` reads any absolute path except `/etc`, `/root`, `/var` (for example `~/.ssh`) | `safe_path` inside the workspace, or removed (real file MCP servers confine themselves) |
| D-16 | S2 | `repos/sandbox.py:349-410` | Document version with `sha256='dummy'`, `pr.simulated` ledger entry | Real PR via `repos/github.py`, or a labelled "draft PR description" with a real SHA-256 |
| D-17 | S2 | `harness/skill_specter.py`, `qe_tools.py:737` | **Corrected:** a local regex/AST scanner presented as "NVIDIA Skill Specter", with its own score bands; "Cloudflare" checks are unsupported | Call real `skillspector scan --format json` (or its MCP `scan_skill`). Store its real score and SARIF. If it is not installed, the evaluator says "security not scanned", never a score |
| D-18 | S3 | `api/skills.py:140-300`; `studio/page.tsx:308` | Keyword-built suggestions when the model fails | A typed error from `core/errors.py` |
| D-19 | S3 | `qe_tools.py:43,546` | Silent fallback to the seeded project `prj_agentic_qe` | 400 error |
| D-20 | S3 | `qe_tools.py:787`, `skill_tester.py:71`, `api/skills.py:664` | Skill scripts run without `clean_env()`, with `cwd` at the repo root | MAF `SkillScriptRunner` + `clean_env()` + timeout + workspace `cwd` + approval |
| D-21 | S3 | `harness/session.py`, `approval_manager.py` | Custom JSON sessions; approvals lost on restart | `FileSessionStore`, `FileHistoryProvider`, MAF approval state |
| D-22 | S3 | `except Exception: pass` in `qe_tools.py` | Hides failures | Typed errors through `core/logs.py` |
| D-23 | S2 | `harness/intent_classifier.py` | Keyword routing shown as reasoning | Removed from the path; slash commands stay deterministic |

Tests pinning fake behaviour (rewrite the assertions, do not delete files): `test_harness_universal_hitl.py`, `test_harness_specter_rag_and_skills.py`, `test_harness_project_scoped_features.py`, `test_harness_ba_studio_real_generation.py`, `test_mcp_servers.py`, `test_playwright_mcp_and_doc_parsers.py`.

---

## 3. Ambition lens (Rieseberg): what the platform is for, how deep, which fields

Rieseberg's point is to aim the model at the outcome, use the instruments experts use, check against an outside judge, and bring in more fields. Each is turned into something code can check, or it is left out. Role play is not used anywhere.

### 3.1 Altitude: the outcome beyond the feature

- The task is not "a harness chat". In verbs: **BAs and developers turn a business document or a repository into tested, approved changes, and every claim on screen can be traced to evidence.** Each phase is judged against that.
- Durable loops, with humans kept at the gates. Two background loops built on `AgentLoopMiddleware`, each with a code predicate and an iteration cap:
  - **Keep skills healthy.** On each plugin change, re-run the evaluator and SkillSpector. A skill that drops below threshold is marked `blocked` and the admin is told. It is never silently fixed.
  - **Keep the project's suite green.** After a merge, run the approved tests. A failure opens a defect record and a change run that **stops at the human gate**.
- The model gets what it needs to work at this altitude: repository at a known commit (exists), test runners (exist), CI on 3 OSes (exists), and real MCP connectors (P4).

### 3.2 Depth: expert instruments and outside judges

| Instead of | Use the instrument experts use | Outside judge (not the model) |
|---|---|---|
| Home-grown "Specter" | NVIDIA SkillSpector, SARIF 2.1.0 | SkillSpector score and exit code |
| Model-reported test success | Real runner output, JUnit XML | `qe/execution.py` counts; zero executed is `INCONCLUSIVE` |
| Model-written Gherkin "looks right" | `gherkin-official` parser | Parse result |
| Model self-review score | Evaluator dimensions 3-5: assertion pass rate, **skill lift** (with skill vs without, same cases), **trigger F1** | Deterministic grader + a different judge model + human review in the eval viewer |
| Markdown observability tables | OpenTelemetry traces and SQL over `tool_calls`, `run_events`, ledger | Trace IDs that link UI rows to spans |

Ambitious targets, enforced in CI:

1. **Zero fabricated values in production code.** A CI grep and AST gate fails the build on new literal scores, `status: "connected"`, `success: True` in an `except` block, or `sleep` in streaming paths under `src/backend` (not tests).
2. **Model-visible means logged.** 100% of model requests can be rebuilt from stored history plus prompt and skill SHA-256s. A test rebuilds one and compares hashes.
3. **100% of tool, skill, and MCP calls traced:** a `tool_calls` row plus a span. A test fails if a tool runs without one.
4. **Agents approve nothing.** A test calls every registered tool and asserts that none changes `gates` or `approvals`.

### 3.3 Range: fields the platform borrows from

These are methods, not personas.

| Field | Method it brings | Where |
|---|---|---|
| Security red team | SkillSpector, prompt-injection cases in `evals/harness/`, zip-slip tests | P4-R, P6-R |
| Audit and compliance | Separation of duties: the requester cannot approve their own gate or plugin; hash-chained ledger | P5 |
| SRE | SLOs on first token and run completion; OpenTelemetry; health checks | P2, P10 |
| Data science | Skill lift and trigger F1 with confidence intervals, reported only with sample size *n* | P6 |
| Licensing and legal | Each plugin records its license and origin; proprietary skills are not vendored without clearance | P3, decision 6 |
| Desktop product | Electron host pattern from DeepSeek Harness | P9 |

**Depth pass in Skill Studio.** Before proposing a task list, the creator agent must answer Rieseberg's four depth questions about the uploaded document: (1) what a top professional would do that the document does not ask for; (2) the rawest material to start from; (3) the methods and tools; (4) what besides the model shows the result is right. The answers are shown beside the task list for the user to edit, and question 4 becomes the skill's `evals.json` acceptance cases.

---

## 4. Goal 3: target architecture

### 4.1 Runtime composition (MAF primitives, no hand-rolled loop)

```text
src/backend/maf/harness/                 new package, every file under 200 lines
  factory.py     build_harness_agent(user, project, profile) -> agent_framework.create_harness_agent(
                   client=llm.client_for(user),                      existing registry and limits
                   agent_instructions=prompts.current("project-copilot"),
                   skills_provider=plugins.skills_provider_for(user),          SkillsProvider(FilteringSkillsSource(...))
                   tools=[*maf.tools.chat_tools(), *mcp.tools_for(user, project, profile)],
                   file_memory_store=stores.memory(user, project),             FileSystemAgentFileStore
                   file_access_store=stores.workspace(project),               rooted with safe_path
                   background_agents=agents.specialists(),                    existing maf/agents
                   auto_approval_rules=policy.rules_for(user),                ToolApprovalRule list
                   middleware=[governance.telemetry, governance.tool_audit, *hooks.bundle()],
                   history_provider=stores.history(user),                     FileHistoryProvider
                   max_context_window_tokens=models.window(model),            CompactionProvider defaults
                   loop_should_continue=None)                                 loops only in 3.1, with predicates
  stores.py      session, history, memory, workspace stores and paths
  policy.py      admin grants -> approval rules, skill predicate, MCP allowed_tools
  hooks.py       create_agent_hooks_middleware: redact(), ledger, guardrails, "model-visible means logged"
  mcp.py         MCPStdioTool (desktop profile) / MCPStreamableHTTPTool (both) from enabled plugins
  plugins.py     discovery, sidecar validation, reversible registration
  profiles.py    desktop | azure | headless defaults
src/backend/api/harness_v2.py           AG-UI through the existing maf/agui.py wrapper
```

**Tool pipeline.** This follows DeepSeek's `pre-execute → execute → post-execute`, mapped onto MAF function middleware:

| Stage | DeepSeek | MAF here |
|---|---|---|
| Log before execution | `tool/call` session event | `tool_audit` writes the `tool_calls` row as `started` |
| Policy, permission, sandbox | `tools/pre-execute`, guards, `ctx.approval` | `ToolApprovalMiddleware` + admin rules; a missing or unanswerable approval is a **deny** |
| Around dispatch | `tools/execute` (timeout, retry, metrics) | `governance.telemetry` + timeout |
| After | `tools/post-execute` (block, replace, add context) | `redact()`, result compaction (`ToolResultCompactionStrategy`) |
| Final outcome | `tool/result` | `tool_calls` row closed + span |

`ATLAS_HARNESS_ENGINE=legacy|maf` switches engines. It defaults to `legacy` until the MAF engine passes, then flips. Nothing is deleted.

### 4.2 Plugin model: "everything is a plugin"

The format is taken from the marketplace and grouping from DeepSeek:

```text
plugins/<plugin-id>/
  plugin.json            {"id","version","license","origin","trust":"first-party|third-party",
                          "skills":"skills/","mcp":"mcp.json","agents":"agents/","profiles":["desktop","azure"]}
  skills/<skill-id>/                       marketplace layout, unchanged
    SKILL.md                               Agent Skills spec 1.0 (MAF loads this)
    marketplace.yaml                       validated against the marketplace schema (vendored copy of the schema only)
    manifest.yaml, skill-card.json         read for display and license
    evals/evals.json                       used by the evaluator
    scripts/ references/ assets/ templates/ examples/
  mcp.json               {"servers":{"<id>":{"transport":"stdio|http","command":...,"args":[...],"url":...}}}
  agents/*.md            optional declarative child agents
```

- **Discovery and hot reload.** The backend scans `plugins/*/plugin.json` and `data/plugins/*` (installed, not in git). `CachingSkillsSource` uses a refresh interval, so adding, replacing, or removing a folder appears without a restart.
- **Undoable registration** (DeepSeek). A plugin's tools, skills, and MCP servers are recorded as one registration. Disabling the plugin removes all of them, and the ledger records it.
- **Marketplace install.** `POST /api/admin/plugins/install {source: "marketplace", skill_id}` runs the marketplace's own installer (`npx --package=github:shivswami/awesome-agent-skills#marketplace awesome-skill <id>`) into `data/plugins/marketplace/`, with an argument list, a timeout, and `clean_env()`, using the git credentials the admin already has. Then evaluation runs, then admin approval. Nothing proprietary is committed to this repository.
- **Existing `skills/`** is read in place as the implicit plugin `local-skills` (decision 7).

### 4.3 Profiles and deployment

| Profile | Where | Differences |
|---|---|---|
| `desktop` | Electron app | stdio MCP allowed; workspace on the user's disk; backend bound to loopback |
| `azure` | Existing App Service layout | Remote MCP only (`MCPStreamableHTTPTool`); stdio and skill scripts off by default, since repository code shares the machine until sandbox jobs exist (CLAUDE.md) |
| `headless` | CLI and CI (`bin/harness`) | No UI; same plugins and policy |

**Desktop (Electron, recommended).** Following DeepSeek's `apps/desktop` + `apps/desktop-host`:

- `apps/desktop/` is a new folder. Electron main starts the bundled backend (a PyInstaller binary or the venv) on a random loopback port and the Next.js standalone server, then loads the UI.
- The same web UI serves both: one codebase, not a fork.
- Signed builds for Windows, macOS, and Linux come from the existing CI matrix.

---

## 5. Goal 2: harness mapping (references → current → MAF target)

| Concern (source) | Pattern | Current | MAF target |
|---|---|---|---|
| Agent loop (sermakarevich tut04; DSH turn/step) | 1.01, 1.18 | Hand-rolled `harness_agent.py`, `stream_engine.py` | `create_harness_agent` function invocation with an iteration limit |
| Plan / execute modes | 1.03 | `mode_provider.py` copy | `AgentModeProvider` |
| Todos (Lecture 08, tut14) | 2.01 | Todos invented as completed | `TodoProvider` + `TodoFileStore`; the UI reads real state |
| Compaction, tool-output offload (tut09-10) | 1.16 | none | `CompactionProvider`, `ToolResultCompactionStrategy` |
| Sessions (tut07; DSH append-only log) | 1.07 | Custom JSON | `FileSessionStore` + `FileHistoryProvider`; model-visible means logged |
| File memory (tut11) | 4.23 | `memory_provider.py` copy | `FileMemoryProvider` scoped by user and project |
| File access (tut05; DSH `fs/*` seam) | 7.05 | Custom path checks | `FileAccessProvider` over a `safe_path`-rooted store; writes need approval |
| Permission gate (tut06; DSH `ctx.approval`) | 1.05, 1.17 | Agents can approve gates | `ToolApprovalMiddleware` + admin rules; unanswered is deny |
| Hooks (MAF p. 227; DSH events) | 1.02 | none | `create_agent_hooks_middleware` |
| Skills (tut12; marketplace) | 2.22, 5.20 | Prompt-rendered skills only | `SkillsProvider` + `FilteringSkillsSource` from grants; `run_skill_script` always needs approval |
| MCP (tut16) | 2.03 | Fake | `MCPStdioTool` / `MCPStreamableHTTPTool` with `allowed_tools`, `approval_mode` |
| Sub-agents (tut15; DSH Agent Teams) | 5.03 | `magentic.py`, `handoff.py` copies | `BackgroundAgentsProvider` over existing specialists; fixed processes stay workflows |
| Verify before done (Lecture 09) | 1.18 | Agent declares victory | `AgentLoopMiddleware` with code predicates |
| Observability (Lecture 11) | 5.18, 5.19 | Harness not traced | MAF OpenTelemetry + `tool_audit`; Azure Monitor exporter |
| Cost (tut08) | 3.10 | Harness bypasses limits | `governance.telemetry` on the harness agent |
| Evaluation (tut17; evaluator-skill) | 12.04 | Fake seeded scores | `maf/evals` + 8-dimension evaluator + SkillSpector |
| Everything is a plugin (DSH) | 2.07, 5.20 | Skills only | Section 4.2 |
| Profiles and bundles (DSH) | 8.12 | none | `desktop` / `azure` / `headless` |
| Strangler migration | 8.09 | — | `ATLAS_HARNESS_ENGINE` |

---

## 6. Goal 4: admin governance of plugins, skills, and MCP

New migration (next free number in `src/backend/migrations`):

| Table | Columns | Purpose |
|---|---|---|
| `plugins` | id, version, folder sha256, source (`repo`, `marketplace`, `upload`, `studio`), license, origin, trust, status (`pending`, `approved`, `blocked`), eval_score, skillspector_score, requested_by, approved_by, approved_at | Installed plugins and their state |
| `plugin_grants` | plugin, subject_type (`user`, `role`, `all`), subject_id, can_use, can_run_scripts | Who may use what |
| `mcp_grants` | plugin, server, tool or `*`, subject, approval_mode | MCP `allowed_tools` and `approval_mode` |

- `/api/admin/plugins*` goes in `ADMIN_ONLY` (`core/auth.py`). MCP and skill **writes** become admin-only. Today any signed-in user can add MCP servers, run `npx`, and delete skills.
- **Separation of duties:** `approved_by` must differ from `requested_by`.
- Every grant change, install, approval, block, and disable goes to the ledger. Every skill load, script run, and MCP call is a `tool_calls` row and a span. The admin page shows per-plugin use by user, error rate, and last evaluation.
- The UI is a new tab in the existing Settings or Users pages.

---

## 7. Goal 5: Skill Creator Studio (marketplace lifecycle on MAF)

The `skill-creator` and `evaluator-skill` plugins are onboarded as **installed plugins** (decision 6). The phases follow the marketplace `skill-creator`:

| Phase | What happens | MAF / platform piece | Human step |
|---|---|---|---|
| 1 Discovery | Upload a BRD or other document → `repos/doc_parser.py` → `redact()`. The agent asks up to 4 clarifying questions | Harness agent + `skill-creator` skill via `load_skill` | Answers |
| 2 Plan | Depth pass (Section 3.3), then a task list and skill blueprint (name, triggers, scripts, evals) | `TodoProvider` items in a draft; nothing written yet | — |
| 3 **Confirm** | User edits the task list (add, remove, reorder, rename); each edit is a version | Document versioning (`core/documents.py`) | **Approve the task list. Generation is blocked until this, enforced in code, not by the prompt** |
| 4 Scaffold | Writes to `data/skill-drafts/<id>/` in marketplace layout | `apply_edits` + `safe_path`; `FileSkillsSource` must load it | — |
| 5 Evals | `evals/evals.json` from the depth-pass acceptance answers | Validator on the JSON | Edit if needed |
| 6 Quality and security | 8 dimensions: spec, content, functional, lift, trigger F1, reliability, efficiency, **SkillSpector** | `evaluator-skill` scripts via `SkillScriptRunner` with `clean_env()`; SkillSpector CLI or MCP | — |
| 7 Baseline lift | Same cases with and without the skill; a different judge model grades | Two MAF agents, grader prompt from `agents/grader.md` | — |
| 8 Human review | Eval viewer output shown in the studio | Stored as a document version | Review |
| 9 Trigger optimisation | Optional bounded loop on the description, stopping when F1 ≥ 0.80 or after 5 iterations | `AgentLoopMiddleware` with a code predicate | Accept or reject |
| 10 Package and publish | `.skill` zip + `marketplace.yaml` (`status: draft`, never self-marked `verified`) | `package_skill.py` | **Admin approves** (not the requester); copied to `data/plugins/studio/` and discovered |

**Zip upload of an existing skill.** `POST /api/skills/upload`, admin or granted user.

1. Size limit, file-count limit; refuse symlinks, absolute paths, and `..` (zip-slip).
2. Extract through `safe_path` into `data/skill-drafts/<id>/`.
3. Validate `SKILL.md` with MAF and `marketplace.yaml` against the schema.
4. Run phases 6 and 7, then show recommendations: the evaluator's failing dimensions, SkillSpector findings with file and line, and missing evals.
5. Admin approval.

Uploaded skills are `third-party`: `run_skill_script` always needs approval, and on the Azure profile scripts are off unless the admin enables them.

---

## 8. Goal 6 and Goal 7: other gaps and the 200-line rule

- G-1: 60 non-test source files are over 200 lines. Only files this plan touches are split: `qe_tools.py` (if `legacy` is kept), `api/mcp.py` → `api/mcp/{routes,catalog,execute}.py`, `api/skills.py` → `api/skills/{catalog,studio,upload,evaluate}.py`, `HarnessView.tsx` → `components/harness/*`, `skills/studio/page.tsx` → `components/studio/*`. Public imports and API paths stay the same. The rest are listed in `tasks.md`.
- G-2: `PROGRESS.md` is 457 KB. Proposal: monthly roll-over (decision 8).
- G-3: `.next/`, `dist/`, `__pycache__/`, `*.tsbuildinfo` are git-ignored. No action.
- G-4: Docstrings citing PDF pages for non-MAF code (`magentic.py`, `mcp_manager.py`, `todo_provider.py`) are corrected.
- G-5: Still open from `tasks.md`: live private-repo PR, Windows double-click, real Azure deploy.

---

## 8a. Commands, hooks, and sub-agents (added after the owner's questions, 2026-11-10)

MAF 1.24 provides skills with progressive disclosure (`SkillsProvider`: `load_skill`, `read_skill_resource`, `run_skill_script`), sub-agents (`BackgroundAgentsProvider`, **marked experimental** in 1.24, so it emits `ExperimentalWarning`), hooks (`create_agent_hooks_middleware`, function and agent middleware), and MCP. **It does not provide slash commands.** The MAF docs say the harness "doesn't prescribe an application interface"; `/todos` and `/mode` exist only in its sample console. So a command registry is planned work, not something MAF gives:

| Plugin part | Source format | How the harness runs it |
|---|---|---|
| Skills | `skills/*/SKILL.md` | `SkillsProvider`, progressive disclosure |
| **Commands** | Skills with `disable-model-invocation: true` and `argument-hint` (Claude Code convention, used by agentic-qe `qe-*`), or a plugin `commands/*.md` | New `maf/harness/commands.py`: `/plugin:command args` runs without a model turn first (DeepSeek `ctx.commands`), then sends the command's body plus `$ARGUMENTS` to the agent. Command skills are removed from the model-visible list by `FilteringSkillsSource`, because MAF drops the `disable-model-invocation` field |
| Sub-agents | `agents/*.md` (frontmatter `name`, `description`, `tools`, `model`) | Adapter builds a MAF `Agent` per file. Instructions come from the body. `tools: Read, Glob, Grep` maps to existing `maf/tools` (`read_file`, `list_files`, `grep`); `Write`/`Edit` map to `apply_edits`; `Bash` maps to the guarded runner. `model` maps to an admin-allowed model or the user's default. Run through `BackgroundAgentsProvider` |
| Hooks | `hooks/hooks.json` (Claude Code events) | Adapter runs each hook command with an argument list, timeout, and `clean_env()`, plus `CLAUDE_PLUGIN_ROOT`, feeding the Claude Code hook JSON on stdin. `PreToolUse` → function middleware before the call (a block decision denies). `PostToolUse` → after. `UserPromptSubmit` → agent middleware before the run. `SessionStart` → session create. `SubagentStop` → wrapper around the child agent run. `FileChanged` → after `apply_edits`. Tool names in the payload use the plugin's names (`Write`, `Edit`, `Bash`) |
| UI modules | `hooks/pane.tsx` (Claude Code pane) | Not portable. The platform's own run view replaces it |

## 8b. The `sarveshtalele/agentic-qe` plugin (v1.6.0, commit `8a7497b`) in this harness

Checked by cloning it and loading its skills with MAF `FileSkillsSource`:

| Part | Count | Works in the MAF harness? |
|---|---|---|
| Skills (`skills/*`) | 26 (11 method skills, 15 `qe-*` commands) | **All 26 load in MAF 1.24.** The method skills work through progressive disclosure as they are |
| `qe-*` commands | 15 | Need the command registry (8a). Without it the model sees them as ordinary skills |
| Agents (`agents/*.md`) | 9 | Need the agent adapter (8a). They match the platform's existing `maf/agents` names |
| Hooks (`hooks/hooks.json`) | 7 events, 9 Node scripts | Need the hook adapter (8a). **The plugin's gates depend on them:** `approval-hook.ts` records a gate only when the human types `approve gate <0-5> for <app>`, and `guard-write.ts` / `guard-bash.ts` block unsafe writes and commands. Without hooks the plugin runs unguarded, so the harness refuses to enable a plugin whose hooks it cannot run |
| Runtime | Node 22.18+ | Local machine has Node 24.21. Azure backend image needs Node, which is to be checked in P3 |
| Gates | G0-G5 in the target repo's `.qe/` ledger | Same G0-G5 names as the platform. Decision 11: which ledger is the source of truth |

**Drift found:** this repo's `skills/` copies are v1.4.0 while the plugin is v1.6.0 (10 of 11 shared folders differ). The 15 `qe-*` copies in `plugins/agentic-qe/skills` are identical to 1.6.0. Once the plugin is installed, MAF `DeduplicatingSkillsSource` keeps one copy (decision 12).

**Marketplace skills under MAF:** 4 of 23 are rejected by MAF's spec checks. `skill-auditor` and `marketplace-yaml-generator` have descriptions over 1,024 characters. `test-data-generator` and `fsd-mapper` give `allowed-tools` as a list instead of a space-separated string. Several more load with `metadata.tags` dropped (MAF expects text values). The evaluator reports these as spec failures with the file name; they are not patched silently.

## 8c. Page review (all 35 `page.tsx` routes and shared components)

Checks run: every `api()` call was matched against the 162 backend routes (none missing); `tsc --noEmit` passed with 0 errors; `eslint` passed with 0 problems; the pages were grepped for literal scores and fixed data. **Not done:** clicking through each page in a browser with a live backend.

| ID | Sev | Page | Problem | Fix |
|---|---|---|---|---|
| D-24 | S1 | `app/skills/page.tsx:100-112, 139, 187-336` | "NVIDIA Skill Specter" score **computed from a hash of the skill name** (94-99, A or A+), shown as "Specter Verified"; subtitle claims "59+ skills validated" | Show the stored SkillSpector result and evaluator score per skill, or "not scanned" |
| D-25 | S2 | `components/HarnessView.tsx:1303, 1311, 2194, 2577, 2595, 2605, 2897` | Hardcoded "0.96 A+" RAGAS benchmark, "97.0% / 99.2%", "Risk: 0/100", default grade "A+" | Read real values from `maf/evals` and the evaluator; empty says "not measured" |
| D-26 | S2 | `components/HarnessView.tsx:156-205, 240-248` | Shows 8-9 quality gates (Gate 0 to 8, with Healing and Coverage gates), while the platform and the agentic-qe plugin both have G0-G5 (`settings/page.tsx:99`) | One gate list from `/api` gate status |
| D-27 | S2 | `app/agents/[key]/page.tsx:157, 170` | Calls rules an "NVIDIA Skill Specter Tier 1 standard" and a "Cloudflare P0 standard"; neither exists as such | Describe the platform's own rules plainly |
| D-28 | S2 | `content/docs.ts:315` vs `app/mcp/page.tsx` | Docs say the app connects to no MCP server; the MCP page shows servers "connected". Both are wrong after P4 in different ways | Docs regenerated from real behaviour after P4 |
| D-29 | S2 | `content/docs.ts:748, 762, 780` | "Cloudflare WAF", "NVIDIA Skill Specter A+ Compliance" presented as platform features | Remove or mark as optional design, not current state |
| D-30 | S3 | `app/mcp/page.tsx` (801 lines), `app/skills/studio/page.tsx:308` | Shows backend status as given (fake until P4); local fallback suggestions in the studio | Fixed by P4 and D-18 |

Pages with no problem found by these checks: account, approvals, chat, docs index, documents, findings, login, observability, home, project overview, repository, documents, document editor, feature, governance, prompts, runs, settings, templates, usage, users.

## 8d. Patterns used, and what each saves

From the ashishpatel26 catalog (192 patterns; I read about 23% of the page, the first 100k of 426k characters):

- **31 patterns** in all: 16 the code already has (Section 5 and `plan.md`), and 15 the rebuild adds.
- MAF provides 12 of the 15 additions, so they cost configuration, not code: 1.18, 1.03, 2.01, 1.16, 4.23, 1.17, 1.02, 2.22, 2.03, 5.03, 5.18, and 5.19 through the OpenTelemetry exporter.
- The other 3 are written here: 5.20 plugin self-registration, 8.12 profiles, and 8.09 the engine switch.

From Rieseberg: 8 techniques (altitude: outcome framing, durable loops; depth: expert instruments, hard targets, outside judge, the depth prompt; range: verbs not nouns, a crew of fields). Two are not used: the customer simulation and "produce new knowledge", which do not fit this product yet.

| Saves | Patterns |
|---|---|
| Tokens | 1.16 compaction pipeline and tool-output offload (old tool results cut from context); 2.22 progressive disclosure (each skill costs about 100 tokens until loaded, instead of the whole SKILL.md in every prompt as `core/skills.py` does today); 1.07 resumable sessions (no re-exploration after restart, Lecture 05) |
| Code to maintain | 1.01, 1.03, 2.01, 4.23, 1.05, 5.03 come from `create_harness_agent`. About 4,900 hand-rolled lines are replaced by a factory under 200 lines plus adapters |
| Wasted runs | 1.18 bounded loops with code predicates (stop on evidence, not on the model's word); 3.10 backpressure (one model-call limit); 1.05/1.17 approval rules (standing approvals mean fewer repeat prompts, and a denied call never runs) |
| Debug time | 5.18 tracing + 5.19 log aggregation + "model-visible means logged" (any answer can be replayed) |
| Change cost | 2.07 factory + 5.20 self-registration + 8.12 profiles (add a plugin folder, no code change); 8.09 strangler (old and new engines side by side) |

## 8e. Testing strategy and evidence report (owner request, 2026-11-10)

Rule: a test's verdict is computed by code from what ran. Zero executed is `INCONCLUSIVE`. No `assert True`, no skip added to get green, no removed assertion. The model is replaced only by `tests/scripted_client.py`, only in `tests/`.

### Levels

| Level | Marker / command | What is real | What stands in | Runs where |
|---|---|---|---|---|
| Unit | default, `python scripts/dev.py test` | Pure functions: policy → approval rules, plugin and sidecar validation, zip-slip extractor, command parser, hook payload builder, SkillSpector result parser, fabrication gates | nothing | CI, 3 OSes |
| Integration | default | FastAPI `TestClient`, SQLite, git, MAF `Agent` and `create_harness_agent`, `FileSkillsSource` on real skill folders, **a real stdio MCP server started by the test** (`mcp` FastMCP, real JSON-RPC, not a stub), the real agentic-qe Node hooks (Node is required; CI installs it) | Model → `ScriptedClient` | CI, 3 OSes |
| Live | `-m live` | Same plus the real model from `.env` | nothing | Local and on demand |
| Smoke | `-m smoke`, `python scripts/dev.py smoke` | Built UI + backend in a browser | No model | CI |
| E2E | `-m e2e`, `python scripts/dev.py e2e` | Real backend, real Next.js UI, real model, real repositories (`personal-finance-mcp`, agentic-qe `examples/`), real Chromium through Playwright 1.64.1 | nothing | Local, each phase end |
| Exploratory | Playwright MCP (`claude mcp add playwright npx @playwright/mcp@latest`, added 2026-11-10) | The developer agent drives the running app, takes screenshots, reads console errors | nothing | During development; findings become E2E tests |
| Agent evals | `tests/test_evaluation_metrics.py`, `maf/evals`, `evals/harness/` | Real model, deterministic graders, a different judge model | nothing | CI (deterministic part), local (model part) |

### Harness test design (one row per capability)

| Capability | Unit | Integration (ScriptedClient) | Live / E2E oracle |
|---|---|---|---|
| Loop and function invocation | iteration cap config | scripted tool call runs the real tool once; cap stops a runaway | live: tool call shown in `tool_calls` with a span |
| Plan / execute modes | — | write tools refused in plan mode | E2E: mode badge and refusal message |
| Todos | — | `TodoProvider` state persisted and reloaded | E2E: todo panel matches stored items |
| Compaction | strategy thresholds | long scripted history compacts below the window; tool results trimmed | — |
| Sessions and history | — | restart the app, same session resumes with identical history hash | E2E: reload keeps the thread |
| File memory and access | path rooting | `..`, absolute, and symlink escapes refused; writes need approval | — |
| Tool approval | rule building from grants | unanswered approval = deny; standing approval honoured; **no tool changes `gates` or `approvals`** (gate 4) | E2E: approval card, approve, tool runs once |
| Hooks | payload shape | real agentic-qe `guard-write.ts` blocks a write outside the test folder; `approval-hook.ts` records `approve gate 0` typed by the user only | live: blocked write shown with the hook's reason |
| Skills, progressive disclosure | frontmatter filter | only name and description in the first request; `load_skill` returns the body; disabled skill invisible | live: model loads the right skill for a prompt (trigger F1 eval) |
| Commands | parser (`/plugin:cmd args`) | `qe-start` runs without a model turn first, then sends `$ARGUMENTS` | E2E: `/agentic-qe:qe-start` → Gate 0 prompt |
| Sub-agents | adapter field mapping | `agents/*.md` → MAF `Agent` with mapped tools only | live: delegated task result returned |
| MCP | config parsing | real FastMCP server: `list_tools`, call, error, timeout, `allowed_tools` filter | E2E: Playwright MCP server connects; status from `list_tools` |
| Governance | grant predicates | ungranted user cannot see a skill or MCP tool; requester ≠ approver | E2E: admin grants, user sees it |
| Model-visible means logged | — | rebuild a request from history + prompt SHA + skill SHAs, compare hash (gate 2) | — |
| Observability | — | every tool call has a `tool_calls` row (gate 3) | E2E: observability page lists the run |

### Skill testing

| Check | How | Pass rule |
|---|---|---|
| Loads in MAF | `FileSkillsSource` | Loaded, with no spec error (checked 2026-11-10: agentic-qe 26/26; marketplace 4 of 23 rejected) |
| Marketplace sidecar | `marketplace.yaml` against the vendored schema | Valid |
| Security | NVIDIA SkillSpector `--format json` | Score ≤ 50; not installed = "not scanned", which blocks approval |
| Evaluator 8 dimensions | `evaluator-skill` scripts | Weighted score with *n* shown |
| Functional evals | `evals/evals.json` on the real model | ≥ 80% assertions pass, with *n* |
| Lift | Same cases with and without the skill | Reported delta with *n*; negative lift is flagged |
| Plugin end to end | agentic-qe `qe-start` → G0 on `examples/brownfield-personal-finance-mcp` | Gate 0 file and `.qe/` ledger created only after the typed approval |

### Evidence report

`scripts/evidence_report.py` (standard library only) reads JUnit XML from each level (`pytest --junitxml`), screenshots, the git SHA, and the model id, and writes `docs/evidence/runs/<date>-<sha>/REPORT.md` plus `report.json`:

- per level: executed, passed, failed, skipped, errors, duration, and the verdict computed by code (`PASS` only when executed > 0 and failed + errors = 0; `INCONCLUSIVE` when executed = 0);
- each failing case with its message;
- the list of screenshots with paths;
- a **Not verified** section, filled from the levels that did not run.

`python scripts/dev.py evidence` runs unit and integration, then smoke, then optionally E2E, then the report.

## 9. Phases, subagents, and models

Each phase ends with offline tests, real output in `PROGRESS.md`, and a review. Each phase is one commit on `feature/maf-harness-platform`, made **only after the owner says yes**.

| Phase | Work | Subagent | Model |
|---|---|---|---|
| P0 | Branch; update `plan.md`, `tasks.md`, `docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md` | main | Opus |
| P1 | Stop fabrication: D-01..D-05, D-10..D-12, D-15, D-19, D-22; CI gates 1 and 4 from Section 3.2 | `general-purpose` | Sonnet |
| P1-R | Review against the CLAUDE.md evidence rules | `agentic-qe:confidence-reviewer` | Opus |
| P2 | `maf/harness/` on `create_harness_agent`; tool pipeline; profiles; AG-UI route behind the flag; CI gates 2 and 3 | main | Opus |
| P2-T | `ScriptedClient` tests + one live run on the real model | `agentic-qe:qa-execution-engineer` | Sonnet |
| P3 | Plugin model: `plugin.json`, marketplace sidecar validation, discovery, hot reload, undoable registration, `local-skills` | `general-purpose` | Sonnet |
| P3b | Command registry, `agents/*.md` adapter, Claude Code hook adapter (8a); install `sarveshtalele/agentic-qe` 1.6.0 and run `qe-start` → G0 end to end on a sample repo | main, then `qa-execution-engineer` | Opus, then Sonnet |
| P3c | Page fixes D-24 to D-29 (real scores or "not scanned"; one G0-G5 gate list; remove unsupported NVIDIA and Cloudflare claims) | `general-purpose` | Sonnet |
| P4 | Real MCP: replace D-13, D-14; SkillSpector via its MCP server as the first real MCP integration | `general-purpose` | Sonnet |
| P4-R | Security review: MCP spawning, file access, SkillSpector wiring | `security-review` skill | Opus |
| P5 | Governance: migration, admin-only routes, grants → rules and predicates, separation of duties, admin page | main | Opus |
| P6 | Skill Studio phases 1-10 + zip upload + recommendations; marketplace install path | `general-purpose` | Sonnet |
| P6-R | zip-slip, script sandbox, license recording | `security-review` | Opus |
| P7 | UI split; todos, approvals, plugins, MCP panels on real data (read `node_modules/next/dist/docs/` first) | `general-purpose` | Sonnet |
| P8 | Durable loops from 3.1 (skill health, suite green) with predicates and human gates | main | Opus |
| P9 | Electron desktop app (`apps/desktop`) after decision 5 | `general-purpose` | Sonnet |
| P10 | Live E2E on real model, repository, and browser; evidence; docs | `qa-execution-engineer`, then main | Sonnet, then Opus |
| — | Grep audits, file splits with stable imports, test summaries, progress entries | `cavecrew-investigator` / `cavecrew-builder` / `Explore` | Haiku |

Token practice: the Ponytail ladder (MAF before new code), compressed subagent reports, and Context7 checks of MAF, Next.js, CopilotKit, and Electron before each phase. The installed MAF 1.24 source is inspected first, since it is what runs.

**Definition of done for every phase:**
- Offline tests pass (`python scripts/dev.py test`).
- The Section 3.2 CI gates pass.
- No new file is over 200 lines.
- Each claimed behaviour is shown by a command or a browser run.
- Anything not verified is listed.

---

## 10. Decisions needing the owner

| # | Decision | Default until told |
|---|---|---|
| 1 | Approve revision 2 and create `feature/maf-harness-platform` | Not created |
| 2 | Commit and push after each phase? | Ask at each phase |
| 3 | Seeded rows already in `data/atlas.sqlite3`: keep, or remove with a migration | Kept; seeding stops for new databases |
| 4 | Legacy `src/backend/harness/*` after the MAF engine passes: keep frozen or delete later | Kept, frozen, behind `ATLAS_HARNESS_ENGINE=legacy` |
| 5 | Desktop: Electron (recommended, the DeepSeek Harness pattern) or Tauri | Electron if you approve |
| 6 | **Marketplace licensing.** Every marketplace skill, including `skill-creator` and `evaluator-skill`, says `Proprietary (contact maintainers)`, author TCS. (The `skill-creator/manifest.yaml` says MIT, author Sarvesh Talele, which conflicts.) Can they be installed at runtime from the private repo, and may any be committed here? | Runtime install into `data/plugins/` only; nothing committed |
| 7 | Move `skills/` under `plugins/local-skills/`? | Read in place |
| 8 | Roll `PROGRESS.md` over by month? | Not moved |
| 9 | Install NVIDIA SkillSpector (`uv tool install git+https://github.com/NVIDIA/skillspector.git`)? It is a new dependency, Apache-2.0 | Not installed; evaluator reports "security not scanned" |
| 10 | Azure profile: allow skill scripts and stdio MCP? | Off |
| 11 | With the agentic-qe plugin active, whose gate ledger is the source of truth: the plugin's `.qe/` in the target repo, or the platform's database? | Plugin `.qe/` is the source; the platform shows it and copies each decision to its own ledger. The approve button sends the plugin's exact `approve gate N for <app>` grammar as the signed-in human |
| 12 | The repo's `skills/` copies are agentic-qe v1.4.0; the plugin is v1.6.0. After install, prefer the plugin's copies? | Prefer the installed plugin; local copies stay on disk |
