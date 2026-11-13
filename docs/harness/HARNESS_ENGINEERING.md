# Harness engineering: lessons, patterns and the design of the new MAF harness

This is the engineering basis for the new, separate harness application (migration: `HARNESS_SEPARATION_PLAN.md`). It
starts from what went wrong in the embedded harness, measured on live runs, then maps each part of the new design to the
harness engineering patterns it uses, and ends with the efficiency budget the design must meet.

## 1. Goal

A Claude Code-class harness on Microsoft Agent Framework (MAF), shipped as CLI, desktop and web clients over one core.
It runs real repositories in their own environments, asks before risky actions, remembers what it did, finishes each step
in minutes, and proves every claim. Target per QE stage: 180 seconds or less, 40 tool calls or fewer, accurate output.

## 2. What went wrong (measured, 2026-11-10 to 2026-11-13)

| # | Mistake | Evidence | Root cause | Rule for the new harness |
|---|---|---|---|---|
| M1 | The harness lived inside the platform process | repository tests ran in the platform's Python (`mcp` 2.3 instead of 1.x) | shared process, `PATH` and `PYTHONPATH` | Separate application. Repository code runs only in the repository's own environment, inside a sandbox |
| M2 | Two tools for every file action | the model alternated `list_files` and `file_access_ls`, 48 listings in one turn | tools added by two layers | One tool per job, owned by one registry |
| M3 | Heavy fixed prompt | 45 tool schemas (30,360 characters) and 32,426 characters of instructions, about 15,000 tokens per call; 41 skills including the user's personal ones | everything offered every time | Small tool surface per mode; deferred catalogue; only relevant skills; fixed prompt under 8,000 tokens |
| M4 | No definition of done | discovery wrote its files at 82 s and ran to 1,174 s; 356 tool calls, 80% repeats | MAF's todo loop kept going while the model added todos | A step contract: done = its files on disk and its check passes; then the turn ends |
| M5 | Repeated reads | one skill loaded 26 times, `pyproject.toml` read 20 times | nothing stops a repeat | Read cache: a repeated identical read returns a pointer |
| M6 | Background agents started, never collected | the same analyst started 7 times | no lifecycle for spawned work | Every spawned task has an owner, a budget and a collected result |
| M7 | Shell directory drift | after `cd tests`, the model decided the repository had no `pyproject.toml` | persistent shell kept `cd` | Every command starts at the workspace root |
| M8 | Approval state lost | "Collected approval authority is no longer pending" on batches of 3+ parallel approvals | MAF AG-UI 1.8 collected-approval defect; approval store in memory | Own the approval state machine; persist pending approvals in the session log |
| M9 | Host semantics mismatch | the model asked "approve create" in chat; files never written | the plugin was written for Claude Code and Codex | A host adapter that states the host's rules; the approval card is the yes |
| M10 | Gate approval invisible | the hook recorded Gate 0; the model kept waiting | plugin ledger not shown to the model | Facts the harness knows are pinned into context every call |
| M11 | Model faults ended stages | mid-stream stall (180 s) and HTTP 429 ended the run | retries only before the stream; no turn-level recovery | Gateway with retry, Retry-After, stall detection and resume from the session log |
| M12 | Guessing instead of measuring | the proxy and "lost memory" were blamed, then disproved | no per-call metrics | Every call records request size, tools offered, cached tokens, repeats, seconds |
| M13 | Patch on patch | about 15 middlewares (write_first, verify, turn_budget, hygiene, strict args, hints, hooks, nudges...) with no single model of a turn | features added as interceptors | One explicit turn state machine; interceptors only for cross-cutting concerns |
| M14 | Unit tests green, live red | scripted tests passed while live runs failed | the scripted model never behaved like the real one | Replay tests built from recorded live transcripts; a live eval gate per release |
| M15 | Cache-unfriendly context | changing file states inside the system instructions | volatile data early in the prompt | Stable prefix (tools, system), history, volatile tail last |

## 3. Architecture

```
            CLI (aqh)          Desktop (Electron)          Web
                 \                   |                    /
                  ----------- Session API (BFF) ----------          one API: start, send, approve, cancel, rewind, stream
                                     |
            +--------------------- Harness core ----------------------+
            |  Turn state machine   Request builder   Step contract   |
            |  Session event log    Tool registry     Guard chain     |
            |  Context: read cache, compaction, pinned facts          |
            +---+----------+-----------+------------+----------+------+
                |          |           |            |          |
          Model port   Tool port   Store port   Sandbox port  Telemetry port
          (MAF client, (MAF tools, (event log,  (Seatbelt,    (OpenTelemetry,
           gateway)     MCP, shell) checkpoints) bubblewrap,   per-call metrics)
                                                 containers)
```

Hexagonal: the core knows only ports; adapters are MAF clients, MAF tools and MCP, stores, sandboxes. The core never
imports a provider SDK, a web framework or a database driver.

### 3.1 MAF usage

| Need | MAF primitive | Not used, and why |
|---|---|---|
| Model calls, streaming, tool calling | `OpenAIChatCompletionClient` (and other MAF chat clients) behind the model port | |
| Tools | `FunctionTool` / `@tool`, `MCPStdioTool`, `MCPStreamableHTTPTool` | |
| Interceptors | function and chat middleware for the guard chain and metrics | |
| Context injection | `ContextProvider` for pinned facts and skills | |
| Compaction | `TokenBudgetComposedStrategy` with tool-result compaction and summarisation | |
| Skills | MAF skills source, filtered to the active plugin | |
| UI protocol | AG-UI events for the web client | MAF AG-UI's collected-approval store (defect M8): approvals are owned by the core |
| Turn loop | `Agent.run` per model round | `create_harness_agent`'s todo loop (M4): the core's state machine decides when a turn ends |

## 4. Patterns, by part of the harness

The pattern names follow the harness pattern catalogue the owner shared (agent loop, tool system, model layer, memory,
multi-agent, async, safety, architecture, functional, frontend, performance, testing, idioms). Only the patterns the
design uses are listed; each line says where and why.

### 4.1 Agent loop

| Pattern | Where | Why |
|---|---|---|
| Game Loop | the turn loop: build request, call model, run tools, repeat | with guards checked every round: turn budget, step contract, cancel flag; `max_tokens` and `pause_turn` handled, a cut-off tool call never runs |
| State | `Idle, CallingModel, AwaitingApproval, RunningTool, Done` | a tool cannot run before approval; a message during a tool is queued (fixes M8, M13) |
| Double Dispatch | event x state table | an unknown pair is refused and logged |
| Chain of Responsibility | guard chain before each tool: deny rules, path guard, sandbox, hooks, approval | managed guards first and fail closed |
| Context Object | `TurnContext`: session, workspace, mode, budget, cancel, trace | one object instead of long parameter lists |
| Memento | checkpoints before edits; `/rewind` | files and transcript restored together |
| Template Method | base step runner with hooks for plugin hosts | each host adapter (agentic-qe, plain) fills hooks; the outline is fixed (M9) |
| Rule Engine | operational rules: compact at 80%, small model for simple tasks | rules as data, tested on recorded turns |
| Callback | `on_text_delta`, `on_tool_start`, `on_turn_end` for the three clients | the loop imports no UI |

### 4.2 Tool system

| Pattern | Where | Why |
|---|---|---|
| Command | every tool call is an object: name, arguments, id | queued, approved, logged, replayed |
| Registry | one registry; duplicate names fail at registration | one tool per job (M2) |
| Virtual Proxy | deferred tools: name and one line until loaded | small fixed prompt (M3); schemas added after the cached prefix |
| Proxy | guarded tool in front of every real tool | no path to a tool skips the guard chain |
| Adapter | MCP servers and HTTP tools as native tools | errors become `is_error` results |
| Special Case | "no matches", "file unchanged since call N" | short, useful results instead of errors or repeats (M5) |
| Servant | path guard and result truncation shared by all file tools | one rule, one fix |
| Parameter Object | typed request per tool (`ShellRequest`, `ReadRequest`) | validated once, `extra` forbidden |
| Execute Around | sandbox setup and teardown around every command | cleanup on error and cancel (with a reaper) |
| Marker Interface | read-only, destructive, network tags | the gate and the scheduler read them; read-only calls may run in parallel |
| Facade | `run_tests`, `check_gate` | one call instead of five |

### 4.3 Model layer

| Pattern | Where | Why |
|---|---|---|
| Gateway | one model port; the LiteLLM proxy or a provider behind it | one place for keys, routing, metering |
| Retry | in the gateway only: 408, 429, 500, 503, 504, 529, stream errors; Retry-After honoured; capped jittered backoff | M11; never retried in two layers |
| Circuit Breaker, Fallback | per model; fallback only within the tenant's allowed models | a dead endpoint fails fast |
| Partial Response | stream to the clients; tool inputs used only when complete; a stall before the first token is retried, after it the turn resumes from the log | M11 |
| Caching | stable prefix ordering; cached tokens recorded per call | M15; target 80% cached |
| Money | tokens and cost as typed amounts in the ledger | per-session and per-step budgets |
| Tolerant Reader | only at the edge for model JSON | strict types inside |

### 4.4 Context and memory

| Pattern | Where | Why |
|---|---|---|
| Event Sourcing, Write-Ahead Log | the session is an append-only event log; a tool call is logged before it runs | resume after crash or 429; replay for tests (M14) |
| Identity Map | read cache per thread: path and modification time to the earlier result | M5 |
| Lazy Loading | file references and deferred tool schemas | context holds what is used |
| Flyweight | one frozen prompt bundle (tools, system) shared by sessions | same bytes, cache hits |
| Dirty Flag | pinned facts recomputed only when files, gates or checks change | stable prefix, cheap rounds |
| Repository, DAO | session store, checkpoint store | swappable SQLite, Postgres, files |
| Version Number | every artifact write carries the version it read | no silent overwrite by agent or person |

Context layout for every request: `[tools][system: role, rules][stable project facts][history, compacted][pinned step
facts: files, gates, check][new message]`. Only the last two change between rounds.

### 4.5 Subagents

| Pattern | Where | Why |
|---|---|---|
| Master-Worker, Fork/Join | the orchestrator hands tasks to subagents with a brief and a budget, and joins every result | M6: no fire-and-forget |
| Mediator | subagents talk only to the orchestrator | no cross-talk, small contexts |
| Saga | multi-step changes with compensations (branch, write, check) | a failed step undoes the earlier ones |
| Distributed Tracing | one trace across orchestrator, subagents, model and tool calls | M12 |

### 4.6 Async and scheduling

| Pattern | Where | Why |
|---|---|---|
| Guarded Suspension | a tool call waits for approval with a deny-by-default timeout | no hung turns |
| Event Queue | user messages and notices during a turn wait for the next round boundary | transcript never interleaved |
| Balking | a second turn on a running session is refused | one writer per session |
| Thread-Pool Executor | independent read-only tool calls in parallel; writes one by one | speed without races |
| Poison Pill, RAII | clean shutdown of shells, sandboxes, MCP servers | no orphaned processes |

### 4.7 Safety

| Pattern | Where | Why |
|---|---|---|
| Specification, Combinator | permission rules as small predicates (`read_only & in_workspace | approved`) | readable, testable policies |
| Filterer, Role Object | tool surface filtered by mode and role; roles never exceed the user's | least privilege |
| Bulkhead | a sandbox per session; separate pools for interactive and batch | one runaway step cannot sink others |
| Idempotent Consumer | idempotency keys on side-effect tools | a resumed turn never repeats an email or a push |
| Private Class Data | credentials used only through `sign()`, never in context or logs | no secrets reach the model |
| Notification | all validation errors of a tool call returned together | one retry fixes them all |
| Immutable | the session log and checkpoints are append-only and hashed | audit |

### 4.8 Architecture and frontend

| Pattern | Where | Why |
|---|---|---|
| Hexagonal, Dependency Injection | ports and adapters; one composition root per client | testable core; swap model or store |
| Backends For Frontends | one thin backend per client over the session API | CLI, desktop and web differ only in display |
| Feature Toggle | experimental tools and modes per user, frozen per session; kill switches checked live | safe rollout |
| MVI | client state from one reducer over session events | replayable UI |
| Naked Objects | approval cards built from the tool's JSON schema | every tool gets a correct card |

### 4.9 Testing and evals

| Pattern | Where | Why |
|---|---|---|
| Service Stub | scripted model and stub MCP for unit tests | fast, deterministic |
| Object Mother | named sessions: pending approval, long transcript, plugin step at Gate 1 | shared fixtures |
| Arrange/Act/Assert | evals: fixture conversation, one run, checks on transcript and disk | clear failures |
| Replay | recorded live transcripts as fixtures; refreshed per model | closes M14 |

## 5. Turn state machine

```
Idle --message--> CallingModel --tool_use--> RunningTool --result--> CallingModel
                       |                         |  (risky)
                       |                         +--> AwaitingApproval --allow--> RunningTool
                       |                                     |--deny/timeout--> CallingModel (denied result)
                       +--end_turn--> StepCheck --done--> Done (summary, next command)
                                         |--not done, budget left--> CallingModel (one focused nudge)
                                         +--budget spent--> Done (partial, reported)
any state --cancel--> Done (cancelled, logged)        any state --model fault--> Recover (retry or resume from log)
```

Each transition is an event in the session log. A client that reconnects replays the log.

## 6. Step contract (plugin hosts)

A plugin command declares: files it writes, its check command, the gate it ends with, and its allowed tools. The host
adapter turns the command text into this contract once. The core uses it for: the tool surface (only the step's tools),
the pinned facts (files written or missing, check result, gates approved in the plugin's ledger), the done test, and the
budget (40 tool calls, 180 seconds). The model never has to remember the contract; it is shown every round.

## 7. Efficiency budget (acceptance)

| Measure | Embedded harness (measured) | New harness target |
|---|---|---|
| Fixed prompt per call | about 15,000 tokens (45 tools) | under 8,000 tokens (about 15 tools) |
| Tool calls per stage | 97 to 356 | 40 or fewer |
| Repeated calls | 20% to 80% | 10% or less |
| Stage time | 252 s to 1,174 s | 180 s or less |
| Prompt cache hits | 69% | 80% or more |
| Stage lost to a model fault | yes (stall, 429) | no: resumed from the log |
| QE cycle | stopped before Gate 1 | Gates 0 to 5 in the plugin ledger, on two repositories |

Every number is printed per stage by the live runner and stored with the evidence.
