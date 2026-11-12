# Agentic QE Platform

A quality engineering platform and project harness built on the **Microsoft Agent Framework (MAF)**. It has three parts:
- a FastAPI backend;
- a Next.js web app;
- a terminal harness (`bin/harness`) and a desktop app (Electron).

Every number it shows comes from a stored measurement, or it says "not measured".

**Contents:** [What it does](#what-it-does) · [Requirements](#requirements) · [Quick start: macOS](#quick-start-macos) · [Quick start: Windows](#quick-start-windows) · [Two environments](#two-environments-local-and-azure) · [RAGAS evaluations](#ragas-evaluations) · [Azure](#deploy-to-azure-zip-and-kudu) · [Desktop app](#desktop-app) · [Tests](#tests) · [Documents](#documents)

## What it does

| Area | What is real today |
|---|---|
| **Project harness** (`/harness`, `bin/harness`) | MAF `create_harness_agent`. **Discovery:** every loadable tool is listed by name and purpose, and schemas load on demand. **Planning and memory:** todos, plan and execute modes, per-project memory, skills with progressive disclosure. **Specialists:** background agents. **Approvals:** risky tools stop for an Approve/Reject card. **Live status lines and stop/continue.** **Workspace tools:** file and shell tools in the project's sandbox clone (allowlisted programs, each command approved). **Plugins:** the full agentic-qe plugin with its hooks and agents |
| Skill Creator Studio (`/skills/studio`) | Source, then kind (instructions or scripts), then a plan with tasks, sub-agents, formats and eval cases. **Approval** is hashed and enforced. **Generation** is followed by checks: MAF loads it, frontmatter, size, imports, security scan. **Script skills:** their own tests must pass, with a bounded repair loop that cannot weaken tests. **Evaluation** on the real model: the skill against a no-skill baseline, judged by deterministic assertions. Published versions are immutable, with zip download and upload |
| Agents (`/agents`) | 15 governed agents, each with a policy, a versioned prompt and eval cases. Scores are shown only with their measurement (`n` and judge); a blank tile shows its reason |
| MCP (`/mcp`) | Real connections over stdio, HTTP or WebSocket. Tools come only from the server's `list_tools`. Each tool is granted per role and every call is audited |
| Plugins | Upload, enable or disable, grants per role, `.mcp.json` registration, and Claude Code hooks run through MAF middleware |
| BA and QE workflows | Requirements documents (BRDs), the QE lifecycle with gates G0 to G5 approved by named humans, hash-chained ledger, immutable document versions |
| Observability (`/traces`, `/observability`) | OpenTelemetry spans in a local store plus optional OTLP. A trace explorer with tree and waterfall. Admins see all traces, members see their own. Error log with stack traces in `data/<store>/logs/errors-DAY.jsonl` |

## Requirements

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 or newer (tested on 3.14) | `python3 --version` (Windows: `py --version`) |
| Node.js | 22.18 or newer (the agentic-qe plugin runs TypeScript natively) | `node --version` |
| Git | any | `git --version` |
| PostgreSQL | 16 or newer, installed (the app starts its own cluster in `data/postgres`) | macOS: `brew install postgresql@17`; Windows: the installer from postgresql.org; Linux: `apt install postgresql` |
| A model | any OpenAI-compatible endpoint | Set on the Settings page after the first sign-in |

## Quick start: macOS

```bash
git clone https://github.com/sarveshtalele/agentic-harness.git
cd agentic-harness
git checkout feature/maf-harness-platform
cp deploy/environments/local.env.example .env
```

Open `.env` and set `ATLAS_ADMIN_USERNAME` and `ATLAS_ADMIN_PASSWORD`. The password needs 12+ characters and must differ from the username.

```bash
python3 scripts/dev.py setup
python3 scripts/dev.py db
python3 scripts/dev.py env-check --env local
python3 scripts/dev.py up
```

`db` starts a local PostgreSQL in `data/postgres` and adds its URL to `.env` (it never prints the URL). Run it again after a restart. If you had an older SQLite store, `python3 scripts/dev.py db --import-sqlite` copies it in and verifies the ledger chains and document hashes.

`setup` creates `.venv`, installs Python and Node packages, and installs Playwright's Chromium. `up` builds the UI, starts both servers and opens <http://127.0.0.1:3000>.

You can also double-click `start-mac.command`.

## Quick start: Windows

Use **PowerShell** (not Command Prompt). Every step below was written for Windows 10 or 11, 64-bit.

**1. Install the tools once.** `winget` ships with Windows. Close and reopen PowerShell afterwards, so the new programs are on `PATH`.

```powershell
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Git.Git -e
winget install --id PostgreSQL.PostgreSQL.17 -e
```

- **Without winget:** use the installers from python.org (tick **Add python.exe to PATH**), nodejs.org (LTS, 22.18 or newer), git-scm.com and postgresql.org.
- **PostgreSQL:** keep the default folder (`C:\Program Files\PostgreSQL\17`). The app finds its programs there by itself, or through `PGBIN` if you installed somewhere else. You do not need to create a database or remember the installer's password: the app runs its own cluster in `data\postgres`.

**Check:**

```powershell
py --version
node --version
git --version
& "C:\Program Files\PostgreSQL\17\bin\initdb.exe" --version
```

**2. Get the code and the settings file.**

```powershell
git clone https://github.com/sarveshtalele/agentic-harness.git
cd agentic-harness
git checkout feature/maf-harness-platform
Copy-Item deploy\environments\local.env.example .env
notepad .env
```

In `.env`, set `ATLAS_ADMIN_USERNAME` and `ATLAS_ADMIN_PASSWORD` (12+ characters, different from the username). Save and close Notepad.

**3. Install, start the database, check, run.**

```powershell
py scripts\dev.py setup
py scripts\dev.py db
py scripts\dev.py env-check --env local
py scripts\dev.py up
```

- `setup` always creates and uses the project's own `.venv` (never the global Python), installs the Python and Node packages, and installs Playwright's Chromium (used for browser tests and QE screenshots). It prints one line per step with the elapsed time, `[setup 2/4 |   95s] …`, so a slow step looks slow, not stuck. `npm ci` takes 5 to 10 minutes on Windows the first time.
- `db` starts PostgreSQL in `data\postgres` and adds `ATLAS_DATABASE_URL` to `.env`. It prints each step (`[db] Creating a new cluster…`, `[db] Starting PostgreSQL on 127.0.0.1:<port> (server log: …)`, `[db] Ready…`) and takes under a minute. If it fails, it prints the end of `data\postgres\server.log`. After a restart of Windows, run `db` again before `up`.
- If an earlier `setup` printed warnings about `pythoncore-3.14-64\Scripts` not being on `PATH`, it had installed into the global Python (fixed). Run `setup` again: it creates `.venv` and installs there. The global copies are harmless.
- `up` builds the UI and opens <http://127.0.0.1:3000>.

You can also double-click `start-windows.bat`.

**Terminal harness:** `bin\harness.bat`, or `bin\harness.ps1`. If PowerShell refuses the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**Developing:** run `py scripts\dev.py backend` and `py scripts\dev.py frontend` in two PowerShell windows. The backend is on port 8000, the UI on port 3000.

**Windows problems and fixes:**

| Problem | Fix |
|---|---|
| `py` is not recognized | Reinstall Python with **Add python.exe to PATH**, or use the full path `C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe` |
| `initdb.exe` was not found | Install PostgreSQL (step 1), or set `$env:PGBIN="C:\Program Files\PostgreSQL\17\bin"` before `db` |
| Port 8000 or 3000 is in use | Close the other program, or pick free ports for this window: `$env:ATLAS_PORT="8010"; $env:ATLAS_UI_PORT="3010"` |
| `npm` fails with `EPERM` in `node_modules` | Close editors and terminals that hold the folder, then run `setup` again |
| A path is too long (`ENAMETOOLONG`) | Clone into a short folder such as `C:\src\agentic-harness` |

## Two environments: local and Azure

| | Local | Azure |
|---|---|---|
| Template | `deploy/environments/local.env.example` copied to `.env` | `deploy/environments/azure.appsettings.example`, entered as App Service settings |
| Profile | `local`: everything, including stdio MCP, npx and plugin installs | `web`: everything, with sandbox runs capped at `ATLAS_MAX_SANDBOXES` (5). stdio MCP, npx and plugin installs are off |
| Store | `data/local/` | `/home/atlas/data` |
| Check | `python scripts/dev.py env-check --env local` | `python /home/site/wwwroot/scripts/env_check.py --env azure` (Kudu SSH) |

They never share a database, files or secrets. `env-check` prints which settings are missing or weak, never their values.

## RAGAS evaluations

Faithfulness scores need RAGAS.

- **Locally:** install it into the project environment:

  ```bash
  .venv/bin/python -m pip install -r requirements-evals.txt
  ```

  On Windows: `.venv\Scripts\python -m pip install -r requirements-evals.txt`

  Then restart the backend with `python scripts/dev.py backend`, which uses `.venv` automatically. On an agent's page, run its evals with RAGAS on.
- **On Azure:** set `ATLAS_INSTALL_EVALS=1` on the API app.
- **Other tiles:** Recall, F1 and groundedness need eval cases with labelled keys and repository context. Until then the tiles say so.

## Deploy to Azure (zip and Kudu)

GitHub never connects to Azure. You build two zips on your computer and upload them in the browser.

**On macOS or Linux:**

```bash
python scripts/package_azure_kudu.py
ATLAS_ADMIN_USERNAME=<name> ATLAS_ADMIN_PASSWORD=<12+ chars> python scripts/dev.py azure-local --check
```

**On Windows, in PowerShell from the repository folder:**

```powershell
py scripts\package_azure_kudu.py
$env:ATLAS_ADMIN_USERNAME = "<name>"
$env:ATLAS_ADMIN_PASSWORD = "<12+ chars>"
py scripts\dev.py azure-local --check
Remove-Item Env:ATLAS_ADMIN_PASSWORD
```

- **The first command** writes `dist\azure_backend.zip` and `dist\azure_frontend.zip`.
  - Always use this script, not Explorer's **Send to, Compressed folder**. The script stores paths with forward slashes, which the Linux App Service needs. It keeps the startup scripts' line endings, and it ships only files Git tracks or would track: `.gitignore` keeps `.env`, `data\` and build folders out of every zip.
- **`azure-local --check`** unzips both packages into `data\azure-local`, starts them through their own startup scripts in the web profile with a local PostgreSQL, and must print `API health: 200; UI /login: 200`.

**Upload the zips:**
1. Open `https://<api app>.scm.azurewebsites.net/ZipDeployUI` in your browser. Drag `dist\azure_backend.zip` from Explorer onto the page and wait for it to finish.
2. Do the same for `dist\azure_frontend.zip` on `https://<ui app>.scm.azurewebsites.net/ZipDeployUI`.
3. Restart both apps in the portal.

The full setup is in **`docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md`**, the standard guide: East US 2, one B1 plan with two web apps, PostgreSQL Flexible Server B1ms, Blob Storage, Key Vault, about $28.50 a month.

## Desktop app

Windows MSI and macOS DMG. CI builds them; you publish them to the Blob `downloads` container, and the login page offers them. See **`docs/DESKTOP_RELEASE_GUIDE.md`**.

**Developer mode:**

```bash
python scripts/desktop_build.py --ui
```

Then `cd apps/desktop`, `npm install` and `npx electron .`.

## Tests

| Run | Command |
|---|---|
| Offline (no network, no model) | `python scripts/dev.py test` |
| Browser smoke test | `python scripts/dev.py smoke` |
| End to end, real model and browser | `python scripts/dev.py e2e` |
| Evidence report (HTML per user story) | `python scripts/dev.py evidence --e2e` |

**CI gates:**
- no source file over 200 lines (`tests/test_file_size.py`);
- no fabricated data (`tests/test_no_fabrication.py`);
- agents never approve (`tests/test_agents_approve_nothing.py`).

## Documents

| Document | What it covers |
|---|---|
| `docs/PLAN_NEXT_STEPS.md` | Current status and the ordered next steps |
| `docs/PROJECT_STRUCTURE.md` | Every file in a table: what it does, what it uses and what uses it (generated from the real imports by `python scripts/gen_structure.py`) |
| `docs/SECURITY_REVIEW_2026-11-11.md` | Dependency audits, code scan, fixes and accepted risks, with the commands to repeat them |
| `docs/MASTER_PLAN.md` | The approved plan: Part 2 (H1 to H9), Phase Q (QE correctness), Phase R (capability registry) |
| `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md` | The standard Azure deployment (PostgreSQL, Blob, Key Vault, East US 2) with costs and a UI tour |
| `docs/DESKTOP_RELEASE_GUIDE.md` | Building and publishing the desktop installers |
| `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md` | How MAF is used: agents, harness, skills, observability |
| `docs/USER_STORIES.md`, `docs/HARNESS_USER_STORIES.md` | The stories the end-to-end tests prove |
| `docs/analysis/` | Evidence-backed run analyses |
| `CLAUDE.md` | The project rules |
