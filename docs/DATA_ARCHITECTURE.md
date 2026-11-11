# Data architecture

Status: written 2026-11-10. Sections 1 and 2 describe `data/` as measured that day. Section 3 is the target. Section 4 is the clear-out: the owner chose option A on 2026-11-10, and the app now runs on `data/v2`.

## 1. Where data lives now

Everything sits under `ATLAS_DATA_DIR`, which defaults to `data/` and is not in Git. Paths come from `src/backend/config.py`.

| Store | Path | Holds | Scope |
|---|---|---|---|
| SQLite | `atlas.sqlite3` | Projects, documents and versions, gates, approvals, ledger, runs, chats, memories, evals, MCP registry, users, sessions | Rows carry `project_id` where they belong to a project |
| Project workspace | `projects/<project>/` | `repo/` (connected repository), `sandbox/` (clone for test runs), `worktrees/` (generated code, one per run), `harness-results/` | One project |
| Harness state | `harness/<project>/` | `todos/` and `history/` per chat thread, `memory/<user>/` (MAF file memory, also scoped per session by MAF) | One project, one user |
| Run files | `runs/<run>/` | Rejected model replies (`failures/`), finished batches (`parts/`) | One run, and through it one project |
| Checkpoints | `checkpoints/` | MAF workflow checkpoints | One run |
| Logs | `logs/app-DAY.jsonl`, `logs/errors-DAY.jsonl` | Requests, warnings and errors; the errors file adds the stack trace and source line. Redacted, kept 30 days (`ATLAS_LOG_RETENTION_DAYS`) | Whole app |
| Legacy | `chromadb/`, `preview/`, `evidence/`, `audit-fresh/` | Legacy harness RAG index, old previews and evidence, the audit run's fresh store | Mixed |

### Isolation rules (tested)

- **Chat memory.** Facts in the `memories` table and MAF memory files stay inside their project. `tests/test_maf_harness.py::test_memory_stays_inside_its_project` writes both kinds in one project. It then checks that a harness turn in another project sees neither.
- **Project delete.** Deleting a project removes its rows, its `projects/<project>/` folder, its run folders and its `harness/<project>/` state. Nothing else is touched (`tests/test_ops.py::test_deleting_a_project_removes_its_run_folders_and_nothing_else`).
- **Chat threads.** A thread's project comes from the server-side row, never from the client (`maf/agui.py`).
- **Legacy exception.** The legacy harness (`/harness?engine=legacy`, `src/backend/harness/`) builds one agent on the platform's own folder for every project. It is not isolated. Retiring it is item F-06 in `docs/FINAL_HARNESS_PLAN.md`.

## 2. Invented data still stored in `data/atlas.sqlite3`

| What | Rows | Why it is invented |
|---|---|---|
| Seeded projects `prj_agentic_qe`, `prj_fintech_gateway`, `prj_ecommerce_core`, `prj_mcp_market`, `prj_agent_evals` | 5 projects, with their gates, findings and documents | Written by `core/seed_data.py`, no real repository behind them |
| `evaluation_metrics` with `judge_model='ragas-specter-v1'` | 108 | Constant scores written by the old RAGAS fallback (fixed, F-03) |
| `evaluation_metrics` with empty `judge_model` | 106 | Need a check: rows from runs that recorded no judge |
| `mcp_servers.status='connected'` | 5 | No MCP session was ever opened. They now read as `not_connected` on the next `/api/mcp/servers` call |

## 3. Target architecture

Each kind of data has one owner module and one store, and each store is keyed so that project isolation is structural.

| Domain | Owner | Local store | Azure store | Key |
|---|---|---|---|---|
| Identity: users, sessions, roles | `core/auth.py` | SQLite | Entra ID + PostgreSQL | user |
| Projects and members | `api/projects.py` | SQLite | PostgreSQL | project |
| Documents and versions (immutable, SHA-256, author, prompt reference) | `core/documents.py` | SQLite | PostgreSQL + Blob for large bodies | project, document, version |
| Gates, approvals, ledger (hash-chained) | `core/gates.py`, `core/ledger.py` | SQLite | PostgreSQL, ledger append-only | project |
| Runs, events, failures, checkpoints | `maf/engine.py` | SQLite + `runs/`, `checkpoints/` | PostgreSQL + Blob | project, run |
| Chats and harness state (todos, history, memory) | `maf/agui.py`, `maf/harness.py` | SQLite + `harness/<project>/` | PostgreSQL + Blob container per project | project, thread, user |
| Repositories, sandboxes, worktrees | `repos/` | `projects/<project>/` | Container Apps Job volume | project |
| Evals: one row per measurement with judge model, sample size and source | `maf/evals/` | SQLite | PostgreSQL | agent, prompt version |
| Skills, plugins, MCP registry and grants | `core/plugins.py`, `api/mcp.py` | Files + SQLite | Blob + PostgreSQL | plugin, user |
| Logs | `core/logs.py` | `logs/*.jsonl` | Application Insights | day |

### Rules

1. A number shown in the UI comes from a stored measurement row that names how it was measured, or the UI says "not measured". An eval row without a judge model or sample size is not a measurement.
2. Seed data does not exist. A new install starts empty, and every page says so. One exception until plan F4: the MCP registry lists 5 declared servers with status `not_connected` and their documented tool lists.
3. Every project-owned row has `project_id`, and every project-owned folder sits under a folder named after the project. Deleting a project removes both.
4. Secrets live only in `credentials`, encrypted (`core/security.py`). They never go into logs, URLs or argv.

## 4. Clear-out

**Chosen 2026-11-10: option A.** `.env` sets `ATLAS_DATA_DIR=data/v2`, and a relative path is read from the repository root (`config.py`). On first start the store had 0 projects, documents, gates, findings, evaluations, eval metrics, memories, chats, runs and approvals. The old `data/` is untouched and is the backup.

The fresh store has no model configured. An admin enters the model endpoint and key on the Settings page and ticks the models users may use.

There were two options. Option A deletes nothing.

### Option A: fresh store, nothing deleted (recommended)

Start the app with a new data folder. The old `data/` stays as it is, so it is also the backup.

```bash
python scripts/dev.py backend
```

Run it with `ATLAS_DATA_DIR=data/v2` set in `.env`. The first start creates the schema from the migrations, with no seed rows. The local launch configs already use `data/audit-fresh` this way.

### Option B: empty the current `data/`

Step 1 is a backup copy. Step 2 removes only the items in this list:

| Item | Size on 2026-11-10 |
|---|---|
| `data/atlas.sqlite3` (plus any `-wal` and `-shm` files) | 5.0 MB |
| `data/projects/` | 19 MB |
| `data/harness/` | 272 KB |
| `data/runs/` | 296 KB |
| `data/checkpoints/` | 12 MB |
| `data/chromadb/` | 2.4 MB |
| `data/preview/` | 636 KB |
| `data/evidence/`, `data/evidence-run.log` | 252 KB |
| `data/audit-fresh/` | 600 KB |

`data/logs/` is kept for debugging. Nothing outside `data/` is touched. The removal runs only after the owner says yes to this exact list.
