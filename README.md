# Agentic QE Platform

Agentic QE Platform is a quality engineering workspace for business analysts, developers and QE leads, built on the
**Microsoft Agent Framework (MAF)**. Agents work on your real repositories; every claim is checked against the code,
every quality gate is signed by a named person, and every change is written to a hash-chained ledger. Nothing is
simulated: a missing model or repository is a clear error, and a value that was not measured says so.

It runs in three places from one code base: the **web app** (local or Azure), the **desktop app** (macOS and Windows),
and the **`aqh` command-line tool** (macOS, Windows, Linux).

**Contents:** [Modules](#modules) · [Requirements](#requirements) · [Set up on macOS or Linux](#set-up-on-macos-or-linux) ·
[Set up on Windows](#set-up-on-windows) · [First sign-in](#first-sign-in) · [Command-line tool](#command-line-tool-aqh) ·
[Desktop app](#desktop-app) · [Deploy to Azure](#deploy-to-azure) · [Tests](#tests) · [Troubleshooting](#troubleshooting) ·
[Documents](#documents)

## Modules

| Module | What it does |
|---|---|
| **Home** | Where you left off, your work, and the desktop downloads when your access includes them |
| **Projects** | A project per repository: connect it from Git, a ZIP or a local folder (local and desktop only) |
| **Harness** | A Claude Code-class agent on MAF: plans with todos, reads and edits files with approval, runs Bash and PowerShell, background tasks, skills in any language, slash commands, MCP tools, hooks, permission modes, checkpoints and `/rewind` |
| **BA Studio** | Upload sources (Word, PowerPoint, PDF, Markdown), brainstorm one question at a time, pick an approach, and get a BRD and checked Gherkin scenarios signed at Gate 1; optional Jira and Confluence through the Atlassian MCP server |
| **QE Cycle** | Gates G0 to G5 from intake to release, each signed by a named person, with a traceability view: requirement, scenario, case, test, result |
| **Skill Studio** | Plan, generate, evaluate and publish new agent skills |
| **MCP Servers** | Real connections over stdio, HTTP or WebSocket; tools granted per role; each member signs in with OAuth where the server needs it |
| **Approvals, Traces, Observability** | Gates and decisions waiting for you; OpenTelemetry traces; error log |
| **Settings, Users, Usage** | Model, feature access per role and member, gate roles, users, token budgets |

## Requirements

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 or newer | `python3 --version` (Windows: `py --version`) |
| Node.js | 22.18 or newer | `node --version` |
| Git | any | `git --version` |
| PostgreSQL | 16 or newer, installed (the app runs its own cluster in `data/postgres`) | macOS: `brew install postgresql@17`; Linux: `sudo apt install postgresql`; Windows: see below |
| A model | any OpenAI-compatible endpoint and key | set on the Settings page after the first sign-in, or in `.env` |

## Set up on macOS or Linux

```bash
git clone https://github.com/sarveshtalele/agentic-harness.git
```

```bash
cd agentic-harness && git checkout feature/maf-harness-platform
```

```bash
python3 scripts/dev.py up
```

`up` does everything, in order, and you can run it again at any time:
1. the first time, it creates `.venv`, installs the Python and UI packages and Playwright's Chromium, and creates `.env` with an `admin` account and a random password, shown once in the terminal and kept in `.env`;
2. it builds the UI when its code changed;
3. it starts the local PostgreSQL in `data/postgres` and writes its address to `.env`;
4. it starts the backend and waits until it answers, then starts the UI;
5. it opens <http://127.0.0.1:3000>. Press Ctrl+C to stop.

You can also double-click `start-mac.command`. To check your settings without printing any value:

```bash
python3 scripts/dev.py env-check --env local
```

## Set up on Windows

Use **PowerShell**. Install the tools once, then close and reopen PowerShell:

```powershell
winget install --id Python.Python.3.12 -e; winget install --id OpenJS.NodeJS.LTS -e; winget install --id Git.Git -e; winget install --id PostgreSQL.PostgreSQL.17 -e
```

Keep PostgreSQL's default folder (`C:\Program Files\PostgreSQL\17`); the app finds it there, or through `PGBIN`. You do not need its installer password: the app runs its own cluster. Then:

```powershell
git clone https://github.com/sarveshtalele/agentic-harness.git C:\src\agentic-harness
```

```powershell
cd C:\src\agentic-harness; git checkout feature/maf-harness-platform
```

```powershell
py scripts\dev.py up
```

A short folder such as `C:\src` avoids Windows path-length errors. You can also double-click `start-windows.bat`.

## First sign-in

1. Sign in with the `admin` account and the password `up` printed (also in `.env`, as `ATLAS_ADMIN_PASSWORD`). To set your own, edit `.env` (12 characters or more, not containing the username) and run `up` again. For a password that is never stored in plain text, run `python3 scripts/dev.py admin-password` and put the printed hash in `ATLAS_ADMIN_PASSWORD_HASH`.
2. **Settings, Model provider:** the base URL, model name and key of your OpenAI-compatible endpoint; **Test connection**; tick the models people may use.
3. **Users:** add people with a role (QE lead, BA, developer, viewer). **Settings, Features** sets what each role may use.
4. **Projects, New project**, then connect its repository. Open **Harness**, **BA Studio** or **QE Cycle** from the project.

## Command-line tool (aqh)

`aqh` runs the same harness in the folder you start it in, editing your files in place. It starts its own local server and PostgreSQL under `~/.aqh` the first time.

```bash
python3 -m pip install -e .
```

```bash
aqh config model --base-url https://your-endpoint/v1 --name your-model
```

```bash
aqh config set-key
```

```bash
aqh doctor
```

Then `aqh` (interactive) or `aqh -p "prompt" --output-format json` (scripts and CI; allow what may run with `--allowedTools "Bash(npm test)"` or `--permission-mode acceptEdits`). `aqh --continue` resumes this folder's last session; `aqh server stop` stops the local server. The key is kept in the OS keychain and never printed.

## Desktop app

The macOS DMG and Windows MSI are built by CI (`.github/workflows/desktop.yml`) and published as described in `docs/DESKTOP_RELEASE_GUIDE.md`. Members sign in with your server's address and their account; the app keeps only a signed sign-in, never the password. It adds a **Terminal** pane under the harness chat. To run it from source:

```bash
python3 scripts/desktop_build.py --ui && cd apps/desktop && npm install && npx electron .
```

## Deploy to Azure

Two zips, uploaded through Kudu; GitHub never connects to Azure. The standard deployment (East US 2, one B1 plan with two web apps, PostgreSQL Flexible Server B1ms, Blob Storage, Key Vault) costs about $21 a month with PostgreSQL stopped outside working hours, under the $25 cap. Build and check the zips locally first:

```bash
python3 scripts/package_azure_kudu.py
```

```bash
python3 scripts/dev.py azure-local --check
```

The check must print `API health: 200; UI /login: 200`. Every portal step, setting and cost is in **`docs/AZURE_DEPLOYMENT_GUIDE.md`**.

## Tests

| Run | Command |
|---|---|
| Unit and integration (no network, no model) | `python3 scripts/dev.py test` |
| Browser smoke test (no model) | `python3 scripts/dev.py smoke` |
| End to end in a real browser, real model | `python3 scripts/dev.py e2e` |
| Live tests with the model from your local store | `python3 scripts/dev.py live tests/test_qe_cycle_live.py` |
| HTML evidence report | `python3 scripts/dev.py evidence --e2e` |

CI (`.github/workflows/ci.yml`) runs the unit, integration and smoke tests and `dev.py up` on Windows, macOS and Linux. It also enforces: no source file over 200 lines, no fabricated data, and agents never approve a gate.

## Troubleshooting

| Problem | Fix |
|---|---|
| "PostgreSQL did not answer" | Run `up` again: it starts the database. The message names the real cause (refused, password, missing database) |
| `initdb` not found | Install PostgreSQL, or set `PGBIN` to its `bin` folder |
| Port 8000 or 3000 in use | Stop the other program, or set `ATLAS_PORT` and `ATLAS_UI_PORT` |
| The harness stops long tasks early | Remove `ATLAS_HARNESS_MAX_ROUNDS` and `ATLAS_HARNESS_MAX_TOOL_CALLS` from `.env` (an older template set them too low) |
| `py` not recognized (Windows) | Reinstall Python with **Add python.exe to PATH** |
| `npm` fails with `EPERM` (Windows) | Close editors and terminals that hold `node_modules`, then run `up` again |

## Documents

| Document | What it covers |
|---|---|
| `docs/DEVELOPER_GUIDE.md` | How to develop: layout, profiles, settings, database, tests, adding agents, tools, workflows and routes, release and deployment |
| `docs/AZURE_DEPLOYMENT_GUIDE.md` | The Azure deployment, step by step, with costs |
| `docs/DESKTOP_APP_GUIDE.md`, `docs/DESKTOP_RELEASE_GUIDE.md` | Using and releasing the desktop app |
| `docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`, `docs/ARCHITECTURE.md` | How the system is built |
| `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md` | How MAF is used: agents, harness, skills, MCP, workflows |
| `docs/SECURITY_GOVERNANCE_AND_AUDIT.md` | Security, governance, audits and accepted risks |
| `docs/PROJECT_STRUCTURE.md` | Every file and what it does (generated by `python3 scripts/gen_structure.py`) |
| `docs/FINAL_PLAN.md`, `docs/PHASE2_PLAN.md`, `docs/PHASE3_PLAN.md` | The approved plans and their status |
| `docs/USER_STORIES.md`, `docs/HARNESS_USER_STORIES.md` | The stories the end-to-end tests prove |
| `docs/THIRD_PARTY_NOTICES.md` | Third-party licences |
| `CLAUDE.md` | The project rules |
