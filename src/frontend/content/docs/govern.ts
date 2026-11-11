import type { DocGroup } from "./types";

export const govern: DocGroup = {
    title: "Govern and observe",
    pages: [
      {
        slug: "approvals-governance",
        title: "Approvals and governance",
        summary: "Who decided what, and proof it was not changed.",
        body: `## Approvals

**Approvals** lists each decision waiting for you, across projects. Each one records your name, and sending back needs feedback. The stage then reruns with it.

## Governance

**Governance** shows signed gate decisions and the hash-chained audit ledger, which flags any edit or deletion.

## Who may sign a gate

The admin lists, on **Settings**, the roles that may sign each gate, G0 to G5. A gate with no roles listed can be signed by anyone who can write in the project. Your name on a decision always comes from your account. A viewer cannot sign any gate, and the administrator can always sign.

## Prompts

**Prompts** shows each agent's versions. An edit creates a new version, and older ones can be reactivated. Each output records the prompt version that produced it.`,
      },
      {
        slug: "observability",
        title: "Observability",
        summary: "Trace and debug every run, in one project or all of them.",
        body: `## Where to find it

**Observability** in the left menu covers all projects, and each project has its own page. Every run has an **Open full trace** link.

## What is recorded

| Log type | Records |
|---|---|
| Skills | The agentic-qe skill each workflow stage carries out |
| Agents | Tokens, duration, prompt version, status, and source of each model call |
| Tools | Tool name, redacted arguments, duration, and status. Refused requests are included |
| MCP tools | MCP server tools. There are none, because this app connects to no MCP server |
| Workflow steps | Stage starts and ends, test results, warnings, and errors |
| Approvals | Who was asked and what they decided |
| Guardrails | Removed prompt injections and redacted secrets |
| Audit ledger | Hash-chained record of each state change |

## Debug a run

1. Choose the run in the **Run** list.
2. Select a type, or search for a name or message.
3. Open any line for details.
4. Use **Download JSON** to save what the filters show.

The **Errors** view groups failed stages by error code and agent, with the latest message and no stack trace.

## Application log

Each day writes one file, \`data/logs/app-YYYY-MM-DD.jsonl\`, with one line per request and one per warning or error. A line never holds a request body, query string, cookie, or username, and every value is masked for secrets. An administrator downloads one day's file from **Settings**. Files older than \`ATLAS_LOG_RETENTION_DAYS\` (30 by default) are deleted.`,
      },
      {
        slug: "accounts",
        title: "Accounts and access",
        summary: "Sign in, create users, and set what each one can use.",
        body: `## Sign in

Everyone signs in first. The admin login comes from \`ATLAS_ADMIN_USERNAME\` and \`ATLAS_ADMIN_PASSWORD\` in \`.env\`. A session ends after \`ATLAS_SESSION_HOURS\` (12 by default), or after \`ATLAS_SESSION_IDLE_MINUTES\` (480 by default) with no activity. After five wrong passwords, that username is locked for five minutes.

## Roles

The admin sets each account's role on **Users**. The environment administrator is always an administrator.

| Role | What it can do |
|---|---|
| Administrator | Everything, including users, models, limits, agents, prompts, and who may sign each gate |
| QE lead | Starts work, and approves where a gate allows its role |
| BA | Writes requirements and documents, and approves where a gate allows its role |
| Developer | Starts runs and changes code on branches. The default for new accounts |
| Viewer | Reads only. Cannot start, edit, run, or approve anything, in any project |

## Projects and members

The owner of a project has full control of it. The owner adds a member on the project page by typing the exact username and choosing a role: developer, QE lead, BA, or viewer. Only the owner and the administrator see the member list. A member's rights are the lesser of their account role and their project role, so a viewer on either side cannot write. Removing a member takes effect on their next request.

Only the administrator can transfer a project, by username. The previous owner loses access, unless they are added back as a member.

## Manage users

The admin opens **Users** and sets, for each person:

| Setting | What it does |
|---|---|
| Password | Stored only as a salted hash. It cannot be read back, only replaced |
| Role | What they may do, as above |
| Models | The models they may use, and their default. See [Models and limits](/docs/models) |
| Token limits | An allocation, plus daily, weekly, and monthly limits, and limits for one model |
| Active from and until | Outside these dates, they cannot sign in and their runs stop |

Changing a password or disabling an account ends that person's sessions.

## Your account

The **Account** link in the top bar shows your role, your models, your limits, and your usage. It also changes your password. Enter your current password and a new one of at least 10 characters. Your other sessions end, and this one stays. The administrator's password is set in \`ATLAS_ADMIN_PASSWORD\`, so change it there and restart.

## What each person sees

Users see only their own projects, and the projects they are added to as members, with everything in them. The admin sees everything and is the only one who can change model settings, agents, prompts, and private repository access.

## How login details are protected

- Passwords are salted scrypt hashes, and usernames are encrypted at rest.
- Sessions are stored only as hashes, in a cookie scripts cannot read.
- Logs pass through a mask, and audit records use account ids rather than names.

Use HTTPS outside your own machine, so sign-in details are encrypted in transit.`,
      },
      {
        slug: "agents",
        title: "Agents and evaluations",
        summary: "Policy, guardrails, and quality for all 12 agents.",
        body: `## What risk means

Risk shows what an agent **could affect**, not how it is behaving.

Agents marked "Impact: changes code" are in the application because Feature Builder and Bug Scan fixes need something that changes code. They have no tools in workflows, their edits pass code guards, they work only on a separate branch, and nothing is committed until a named person approves.

| Risk | Meaning | Agents |
|---|---|---|
| Low | Handles text only | business-analyst (documents and Gherkin), confidence-reviewer (document and evidence review), principal-test-architect, test-design-architect, qa-execution-engineer (explains test results from evidence) |
| Medium | Reads code, or acts on project data in chat | project-copilot, repo-intelligence-analyst, requirements-analyst, test-automation-engineer, bug-reviewer |
| Impact: changes code | Can change code, always on a branch with a person's review | feature-engineer, defect-diagnostician |

Select any agent's card to open its page, with its details, evaluations, and recent calls.

## Controls

| Control | What it does |
|---|---|
| Tool policy | An agent receives only the tools listed for it |
| Disable | Stops an agent at once. It needs your name and goes to the ledger |
| Token limit | Caps output per model call. Each run also has a token budget |
| Secret guardrail | Removes secrets from input and output |
| Injection guardrail | Removes instruction-like text from briefs, sources, and repository files |

## Evaluations

**Run all evaluations** runs each agent's cases on the real model, and stores results per prompt version. Model replies vary, so an occasional case can fail between runs.

There are 28 cases across 12 agents today:

| Check | What it proves |
|---|---|
| Contains, does not contain | Required text is present, and invented text is absent |
| JSON schema | The reply is usable by the next step |
| Gherkin parser | Scenarios are valid |
| Score limits | Weak or untested work cannot score high |
| Prompt injection | The agent ignores instructions hidden in content |

These catch breakage, but they do not measure accuracy, so a card showing 2/2 means less than it seems. Groundedness, Faithfulness, Recall, and F1 scores are specified in \`docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md\`.`,
      },
    ],
};
