# User stories for the whole application

Status: written 2026-11-10 for `docs/MASTER_PLAN.md` phase M8.

Each story has an **oracle**: a check made by code, never the model's own word. Each story runs as a Playwright test on the real model and real repositories. Its screenshots go into the HTML evidence report.

The harness stories HS-01 to HS-14 stay in `docs/HARNESS_USER_STORIES.md` and are part of this set.

**Roles.**
- BA: business analyst.
- Dev: developer.
- QE: quality engineer.
- Lead: QE lead.
- Viewer: read-only.
- Admin: administrator.

**Profiles.** `web` means the Azure proof of concept; the harness and script runs are off there. `desktop` and `local` have everything.

## Accounts and access

| ID | Page | Story | Oracle |
|---|---|---|---|
| US-01 | `/login` | As any user I sign in, and a wrong password is refused without saying which part was wrong | A session cookie is set only on success. After 5 failures the account is locked (`auth_events`). The username is never in the log |
| US-02 | `/account` | As any user I change my password | The old password no longer signs in and the new one does. The ledger has the change, without the password |
| US-03 | `/users` | As Admin I add a user with a role. A non-admin cannot open the page | The new user signs in. A non-admin gets a 403 from `/api/users` |
| US-04 | `/projects/[id]/governance` | As Admin I add members to a project. A non-member cannot see the project | The project is absent from a non-member's `/api/projects`, and `/projects/[id]` shows "not found" |
| US-05 | `/usage` | As Admin I set a user's token limit, and a run over it stops | The run fails with `AQE-ALLOW-001`. The usage page shows the real tokens from `agent_calls` |

## Projects and repositories

| ID | Page | Story | Oracle |
|---|---|---|---|
| US-10 | `/` | As Dev I create a project and land on it | A `projects` row exists. The URL is `/projects/prj_*`. An empty store shows "No projects yet", not sample cards |
| US-11 | `/projects/[id]/repository` | As Dev I upload a repository zip, or clone a real Git URL | `repo_sources` row. The tree lists the real files. Lines of code are counted from disk |
| US-12 | `/projects/[id]` | As any member I see the project overview with only real numbers | Every KPI equals its API value. A missing value shows "—" |
| US-13 | `/projects/[id]/bugs` | As Dev I scan the repository and see each finding with file and line | Every finding's quoted line matches the file on disk |
| US-14 | `/projects/[id]/feature` | As Dev I ask for a change. It is built on a separate branch in a worktree and tested | The branch exists and the diff touches only the repository. The verdict comes from the real test run |

## Requirements, documents and governance

| ID | Page | Story | Oracle |
|---|---|---|---|
| US-20 | `/projects/[id]/ba` | As BA I write a BRD from a brief and a source file | `brd` document version 1 with SHA-256, author and prompt reference. Run waits at Gate 0 |
| US-21 | `/projects/[id]/documents/[docId]` | As BA I edit a document. Every save is a new immutable version | The version number increases. The earlier version is unchanged and its SHA-256 still matches |
| US-22 | `/projects/[id]/documents/[docId]` | As BA I convert requirements to Gherkin | The official Gherkin parser accepts the file |
| US-23 | `/projects/[id]/approvals`, `/approvals` | As Lead I approve or reject a gate with feedback. An agent never can | The gate status changes only by my request. The ledger names me. An unknown approval returns 404 |
| US-24 | `/projects/[id]/governance` | As any member I verify the ledger | `verify_ledger` reports the chain intact; editing a row in a copy breaks it |
| US-25 | `/templates` | As BA I upload a document template and use it | The template's sections appear in the next BRD |
| US-26 | `/documents` | As any user I see documents only from projects I can see | Each listed document's project is in my project list |

## Quality engineering

| ID | Page | Story | Oracle |
|---|---|---|---|
| US-30 | `/projects/[id]/qe` | As QE I run the QE workflow on a real repository | Tests are generated on a branch and executed. JUnit counts are shown. Zero executed is `INCONCLUSIVE` |
| US-31 | `/projects/[id]/runs/[runId]` | As QE I follow a run live and see each stage | Run events stream in order. The final verdict equals the stored verdict |
| US-32 | `/projects/[id]/runs` | As QE I see past runs with real durations and tokens | The values equal `runs` and `agent_calls` rows |
| US-33 | `/findings` | As Dev I see findings across my projects only | Each finding's project is visible to me |

## Agents, evaluations and observability

| ID | Page | Story | Oracle |
|---|---|---|---|
| US-40 | `/agents` | As Admin I see each agent's policy, tools and measured scores | A score is shown only with its stored measurement (judge, `n`); otherwise "not measured" |
| US-41 | `/agents/[key]` | As Admin I run the agent's evals on the real model | New `evaluation_metrics` rows with judge model and `n` |
| US-42 | `/projects/[id]/prompts` | As Admin I edit a prompt, which makes a new version | `prompts` version increases; the old text is kept |
| US-43 | `/observability`, `/projects/[id]/observability` | As Admin I see every model call and tool call | Rows equal `agent_calls` and `tool_calls` |
| US-44 | `/settings` | As Admin I download today's error log with stack traces | The file is `errors-DAY.jsonl` and has no secret value |

## Skills, plugins and MCP

| ID | Page | Story | Oracle |
|---|---|---|---|
| US-50 | `/skills` | As any user I browse skills with their real SHA-256 and scan state | The values equal the files on disk |
| US-51 | `/skills/studio` | As BA I create an **instructions-only** skill from a project document: choose the kind, review the plan (tasks, sub-agents, formats, eval cases), approve, generate, publish | The plan hash is stored at approval. MAF loads the skill. Version 1 is in `skill_versions` |
| US-52 | `/skills/studio` | As Dev I create a **script-based** skill. Its tests run in the sandbox | pytest counts come from the real run. Zero tests is `INCONCLUSIVE` |
| US-53 | `/skills/studio` | As QE I evaluate a skill on the model, with and without the skill | Assertion pass rates are stored with `n` and judge `deterministic-assertions` |
| US-54 | `/skills/studio` | As Admin I upload a skill zip. A zip-slip zip is refused | A new version for the good zip; nothing is written for the bad one |
| US-55 | `/mcp` | As Admin I add a real MCP server, connect, and grant one tool to a role | Status `connected` with the tools the server listed. The harness can call only the granted tool |
| US-56 | `/mcp` | As Admin I see a failing server's real error | Status `error` with the message; no tools |
| US-57 | `/settings` (plugins) | As Admin I disable a plugin | Its commands leave the "/" menu and its skills leave the harness |

## Harness, CLI, desktop and Azure

| ID | Where | Story | Oracle |
|---|---|---|---|
| HS-01 to HS-14 | `/harness` | See `docs/HARNESS_USER_STORIES.md` | As written there |
| US-60 | `/harness` | As Dev I see live status lines ("Analysing the repository", "Running tests") while the harness works | Each status line matches a real tool call in `tool_calls` |
| US-61 | `bin/harness` | As Dev I use the same harness from the terminal | The reply and tool calls are stored under the same project and thread |
| US-62 | Desktop app | As Dev I install the app, set my local admin, and run the harness | The packaged app starts both services on loopback. HS-01 and HS-04 pass inside it |
| US-63 | Azure (web profile) | As a team member I use the browser link; the harness page says it is desktop-only | `/agui/harness` returns 403 in `web`. Every other story above passes |
