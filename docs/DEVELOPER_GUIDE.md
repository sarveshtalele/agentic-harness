# Developer Guide

How to set up, run, test, change and deploy Agentic QE Platform. The project rules are in `CLAUDE.md`; read them first.
The README has the short setup; this guide has the detail.

## 1. Set up your machine

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 or newer | the project always uses its own `.venv`, never the global Python |
| Node.js | 22.18 or newer | runs the UI, the desktop app, and the agentic-qe plugin's TypeScript natively |
| Git | any | Windows: Git for Windows also gives the harness `bash` |
| PostgreSQL | 16 or newer, installed | the app starts its own cluster in `data/postgres`; set `PGBIN` if its programs are not in the default place |

```bash
git clone https://github.com/sarveshtalele/agentic-harness.git && cd agentic-harness && git checkout feature/maf-harness-platform
```

```bash
python3 scripts/dev.py up
```

On Windows use `py scripts\dev.py up` in PowerShell, from a short folder such as `C:\src\agentic-harness`.
Work only on `feature/maf-harness-platform`; `main` is the owner's backup and is never merged into.

## 2. Everyday commands (`scripts/dev.py`, standard library only)

| Command | What it does |
|---|---|
| `up` | Install if needed, build the UI when it changed, start PostgreSQL, the backend (waited for) and the UI, open the browser |
| `backend` / `frontend` | The FastAPI backend on 127.0.0.1:8000 / the Next.js dev server on 127.0.0.1:3000, for live reload while you code |
| `db` | Start the local PostgreSQL and write its address to `.env` (`up` does this too) |
| `test` | Unit and integration tests: no network, no model, a throwaway database per run |
| `smoke` | Browser smoke tests on their own ports, no model (CI runs these) |
| `e2e` | Playwright end-to-end tests with real servers, the real model and real repositories |
| `live <tests>` | Tests marked `live`, with the model from your local store; `AQE_LIVE_MODEL=gpt-5` picks another model the same endpoint offers |
| `evidence [--e2e]` | Runs the levels into JUnit and writes the HTML evidence report |
| `env-check --env local\|azure` | Reports missing or weak settings, never their values |
| `azure-local [--check]` | Runs the two Azure zips locally in the web profile |
| `admin-password` | A random first-admin password and its hash for `ATLAS_ADMIN_PASSWORD_HASH` |

## 3. How the code is laid out

| Path | Holds |
|---|---|
| `src/backend/api` | REST routers, one file per area. A new route needs an access rule in `core/auth/rules.py` and a feature (or a place in `CORE`) in `core/auth/features.py`; tests fail otherwise |
| `src/backend/core` | Auth, features, versioning, gates, ledger, security, prompts, files, MCP, plugins, settings |
| `src/backend/maf/agents` | One file per agent with its policy; adding a file registers the agent. Its prompt is `prompts/<agent>.md`, its eval cases `evals/<agent>.json` |
| `src/backend/maf/tools` | One file per tool |
| `src/backend/maf/workflows` | One file per workflow (registers itself); `shared/` and `qe/` hold shared stages. A new workflow needs its feature in `features.WORKFLOWS` |
| `src/backend/maf/harness.py`, `maf/harness_kit/` | The harness: MAF `create_harness_agent` plus shells, permissions, hooks, settings files, skills, plugin contracts, checkpoints, sandbox |
| `src/backend/repos`, `src/backend/qe` | Git, ingest, sandboxes, static analysis; validators, runners, traceability |
| `src/frontend` | Next.js UI (`app/` pages, `features/` areas, `components/`) and the CopilotKit runtime route. Next.js here may differ from what you know: read `node_modules/next/dist/docs/` before using an unfamiliar API |
| `src/aqh` | The `aqh` command-line tool |
| `apps/desktop` | The Electron desktop app |
| `plugins/agentic-qe` | The agentic-qe plugin (pinned copy of its repository) |
| `skills/`, `prompts/`, `templates/`, `evals/` | Platform skills, versioned agent prompts, document templates, agent eval cases |
| `tests/` | Unit and integration tests; `tests/e2e` Playwright; `tests/desktop` the desktop app; `tests/fixtures` real stand-in servers |
| `deploy/` | Environment templates and Azure startup scripts |
| `data/` | Runtime state: database cluster, stores, workspaces, the activity log. Never in Git |

## 4. Profiles and settings

`ATLAS_PROFILE` decides what a server may do:

| Profile | Used by | Differences |
|---|---|---|
| `local` | `dev.py up` | everything: real Bash and PowerShell in the harness, stdio MCP servers, plugin installs |
| `web` | Azure | shared server: the harness runs an allowlisted runner instead of a free shell; no stdio MCP, no plugin installs |
| `desktop` | the desktop app | starts only after sign-in through the team's server; one member, no local admin |
| `cli` | `aqh` | a project is bound to the folder `aqh` runs in, edited in place |

Settings come from `.env` (local) or App Service settings and Key Vault (Azure). The templates are `.env.example` and
`deploy/environments/*.example`. Secrets are encrypted at rest with `ATLAS_SECRET_KEY`, never logged, never in URLs or
command lines. Leave the harness limits (`ATLAS_HARNESS_MAX_ROUNDS`, `ATLAS_HARNESS_MAX_TOOL_CALLS`) unset.

## 5. Tests and evidence

- Write the test with the change. Unit tests use `tests/scripted_client.py` as the model; it never appears in application code.
- No `assert True`, no skips added to get green, no removed assertions. Zero executed tests is INCONCLUSIVE, never PASS.
- A change visible in the browser needs a Playwright check (`tests/e2e`) with a screenshot under `docs/evidence/`.
- Run `dev.py test` before every commit; CI runs the same suite, the smoke tests and `dev.py up` on Windows, macOS and Linux.
- Live runs record their evidence under `docs/evidence/runs/<date>-<name>/`.

## 6. Rules that tests enforce

- No source file over 200 lines (`tests/test_file_size.py`): split by feature instead.
- No fabricated data in production code (`tests/test_no_fabrication.py`): empty state says it is empty.
- Agents never approve a gate (`tests/test_agents_approve_nothing.py`); gates G0 to G5 need a named person.
- Every route has an access rule and a feature (`tests/test_access_routes.py`); every workflow has a feature.
- Subprocesses take an argument list, a timeout and a clean environment; repository code never runs in the platform's own Python.

## 7. Naming

Use these names in the UI, messages, documents and code comments: **Agentic QE Platform**; **Home, Projects, Harness,
BA Studio, QE Cycle, Skill Studio, MCP Servers, Approvals, Traces, Observability, Settings, Users, Usage**; the
command-line tool **aqh**. Write plain English: short sentences, active voice, the same word for the same thing. Do not
use "Autonomous", "Enterprise", "AI SDLC" or "Atlas" in visible text (the `ATLAS_` setting names stay).

## 8. Deploy to Azure

1. `python3 scripts/package_azure_kudu.py` builds `dist/azure_backend.zip` and `dist/azure_frontend.zip` (forward-slash paths, startup scripts' line endings kept, only files Git tracks).
2. `python3 scripts/dev.py azure-local --check` runs both zips locally in the web profile; it must print `API health: 200; UI /login: 200`.
3. Follow `docs/AZURE_DEPLOYMENT_GUIDE.md` for the resources (East US 2, under $25 a month), the settings and Key Vault secrets, the Kudu upload and the first sign-in. Any change that raises the cost needs the owner's approval.

## 9. Release the desktop app

Push to the branch: `.github/workflows/desktop.yml` builds the macOS (Apple silicon and Intel) and Windows installers
with SHA-256 manifests. Publishing them to the Blob `downloads` container is in `docs/DESKTOP_RELEASE_GUIDE.md`.

## 10. Troubleshooting

See the README's table. The activity log of the development hooks is in `data/activity-log.md`.
