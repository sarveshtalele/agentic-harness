import type { DocGroup } from "./types";

export const getStarted: DocGroup = {
    title: "Get started",
    pages: [
      {
        slug: "introduction",
        title: "Introduction",
        summary: "What Agentic QE Platform does and how a project flows through it.",
        body: `Agentic QE Platform is a workspace for business analysts and developers. It turns briefs into requirements, scans real repositories, builds features and fixes on separate branches, and runs a full test lifecycle with a person approving each stage.

## What you can do

| Area | What it gives you |
|---|---|
| BA Studio | Requirements from your own templates, with an independent review and validated Gherkin |
| Bug Scan | A review of the whole repository. Every finding quotes real code |
| Feature Builder | Code changes on a separate branch, checked by running your real tests |
| QE Studio | Requirements, plan, design, generated tests, execution, and traceability through six approval gates |
| Copilot | A chat that knows the project's documents, code, and history |
| Confidence review | An independent score beside each stage, with checks by code that can lower it |
| Observability | A record of every agent, tool, and decision |
| Access and limits | Roles, project members, several models, and token limits for each person |

## How it stays trustworthy

- **Evidence is checked by code.** A finding whose quote is not in the file is dropped, and Gherkin must pass the official parser.
- **People approve.** Agents cannot pass a gate. Every decision records a name.
- **Nothing is invented.** If a model or repository is missing, you get a clear error. Empty pages stay empty.
- **Zero tests is not a pass.** A run that executes no tests reports **INCONCLUSIVE**.

## Where to go next

Start with [Install and run](/docs/install), then follow [Your first project](/docs/first-project).`,
      },
      {
        slug: "install",
        title: "Install and run",
        summary: "Run the platform on Windows or macOS with one double-click.",
        body: `## Requirements

| Software | Version |
|---|---|
| Python | 3.12 or newer |
| Node.js | 20 or newer |
| Git | Any recent version |

You also need an OpenAI-compatible model endpoint and API key.

## Start the app

| System | Do this |
|---|---|
| Windows | Double-click \`start-windows.bat\` |
| macOS | Double-click \`start-mac.command\`. If macOS blocks it, right-click it and choose **Open** |
| Any terminal | Run \`python scripts/dev.py up\` |

The first run installs everything and takes a few minutes. The app then opens at http://127.0.0.1:3000. Press **Ctrl+C** in that window to stop it.

## Connect a model

1. Open **Settings**.
2. Enter the base URL, model name, and API key. The key is encrypted at rest.
3. Choose **Test connection**. It sends a real request and reports the reply and latency.

## If a port is busy

Set \`ATLAS_PORT\` for the API and \`ATLAS_UI_PORT\` for the UI, then start again.`,
      },
      {
        slug: "first-project",
        title: "Your first project",
        summary: "From an empty workspace to a reviewed change.",
        body: `## 1. Create the project

On **Projects**, choose **New project**. Give it a name, and add a Git URL or ZIP now or later.

## 2. Check the repository

Open **Repository**. You see the commit, files, languages, test runners, and the project's sandbox.

## 3. Follow the Next line

**Overview** shows a **Next** line with the most useful step. Select any card to open its tab.

## 4. Scan for bugs

Open **Bug Scan** and choose **Scan repository**. Static analyzers and an agent review every source file, and the result shows how many files were reviewed.

## 5. Fix and review

Choose **Fix on a branch** for one finding, or **Fix all** for the most severe ones. The tests run, and you review the diff and verdict before anything is committed.`,
      },
    ],
};
