import type { DocGroup } from "./types";

export const features: DocGroup = {
    title: "Features",
    pages: [
      {
        slug: "repository",
        title: "Repository and sandbox",
        summary: "How code enters a project and where work happens.",
        body: `## Connect code

| Source | How |
|---|---|
| Public Git | Paste an HTTPS URL or \`owner/repo\` |
| Private GitHub | Add a fine-grained token in **Settings**, then pick the connection and repository |
| ZIP | Upload it. No Git host is needed |
| Local folder | Enter the path. It is copied, and the original is not changed |

For private repositories, the token needs read access to contents. To open pull requests, it also needs write access to contents and pull requests. Tokens are encrypted and never placed in URLs.

## What a sandbox is

Each project gets its own sandbox, shown on the Repository page.

| Part | Purpose |
|---|---|
| Full clone | The complete repository with all history |
| Worktree per run | Each change or QE run works on its own branch, so your main checkout stays untouched |
| Python environment | Installed only if you tick **Install repository dependencies** |
| Clean environment | Test code runs without this platform's secrets |

> A sandbox separates projects by folder and environment. It is not an operating system container, so only install dependencies for repositories you trust.

## Replace a repository

Choose **Replace repository**, connect another source, or use **Re-sync** to fetch the latest commit.`,
      },
      {
        slug: "ba-studio",
        title: "BA Studio",
        summary: "Write requirements from a brief, sources, and a template.",
        body: `## Generate a document

1. Write a brief, and upload any sources: .md, .txt, .pdf, .docx, .xlsx, or .pptx.
2. Choose a template, or upload your own as Markdown or Word. Generated documents keep every heading.
3. Choose **Generate document**.
4. An independent reviewer scores the draft, and Gherkin scenarios are written and validated.
5. Approve at the gate, or send it back with feedback.

## Reviewer scores

Code caps the reviewer's score when it finds missing requirement ids, vague wording, leftover template text, empty sections, or figures that are not in your sources.`,
      },
      {
        slug: "documents",
        title: "Documents",
        summary: "Edit, compare, restore, and download versions.",
        body: `## Work with a document

- **Document** shows it formatted. Select any text to edit it where it is, with a live preview.
- Tables, including Gherkin Examples, are editable grids. Change cells, then use **Add row** or **Add column**.
- **Add text**, **Add table**, and **Add image** insert new content. Images can be PNG, JPEG, GIF, or WebP, up to 10 MB, and export to Word.
- **Source** shows the raw text beside a live preview.
- **Save version** creates one version. Typing does not.
- **History** lists each version, with diffs and restore.
- **Ask reviewer** scores the current version.
- **Refine with agent** saves a new version from your instructions.

Saving an approved document returns it to draft, and invalid Gherkin cannot be saved.

## Downloads

| Document | Formats |
|---|---|
| Any | .md, .docx |
| Gherkin | .feature |
| Test cases | .csv, Jira .csv |`,
      },
      {
        slug: "feature-builder",
        title: "Feature Builder",
        summary: "Build a change on a separate branch and review it.",
        body: `## Build a change

1. Describe the change. Name any functions you require.
2. Tick **Install repository dependencies** if the tests need them.
3. Choose **Build feature**.

## What happens

The tests run first for a baseline. The agent then proposes edits, and code applies them through path, secret, and scope checks. The tests run again, and only new failures count against the change.

## Read the verdict

| Verdict | Meaning |
|---|---|
| PASS | Tests ran and none fail |
| NO NEW FAILURES | Some tests already failed before this change |
| FAIL | The change broke tests after up to three attempts |
| INCOMPLETE | Tests pass, but a named function or a new test is missing |
| INCONCLUSIVE | Tests could not run in this environment |

A red box lists any existing assertion the change altered, so check those. After you approve, you can download the changed files, push, or open a pull request.`,
      },
      {
        slug: "bug-scan",
        title: "Bug Scan",
        summary: "Review the complete repository and fix what it finds.",
        body: `## Run a scan

Choose **Scan repository**. Ruff, secret, code, and manifest scanners run with an agent review of **every source file**. Large files are read in parts. The run reports how many files were reviewed and lists any that were not, for example if the token budget ran out.

An agent finding is kept only if the code it quotes exists in the file.

## Fix findings

| Action | Result |
|---|---|
| **Fix on a branch** | Fixes one finding |
| **Fix all** | Fixes up to 15 of the most severe open findings on one branch. Run it again for the next set |
| **Dismiss** | Hides a finding you do not need |

Each fix runs your tests and waits for your review. Findings are marked as fixed when you approve.

## Diagnose an error

Paste a traceback into **Diagnose an error**, and the diagnostician finds the cause and proposes a fix on a branch.`,
      },
      {
        slug: "qe-studio",
        title: "QE Studio",
        summary: "Run the full test lifecycle with six approval gates.",
        body: `## The gates

| Gate | You approve |
|---|---|
| G0 Intake | Scope and mode |
| G1 Requirements | Requirements with verified evidence |
| G2 Plan | Risk-ranked plan |
| G3 Design | Test cases and oracles |
| G4 Generate | Generated tests. Approving lets them run on this machine |
| G5 Release | Executed evidence and verdict |

## Watch it live

The run panel shows the current stage, elapsed time, tokens, and a **live log** of each step, including while an agent waits for the model. Documents appear as cards on the right as they are created.

## Confidence reviews

An independent reviewer scores the work before every gate: discovery, requirements, the plan, each batch of test cases, and the generated tests. A score below 70 sends the work back once, automatically. Test design and generation run in batches, and each batch is reviewed. For a code change, the review runs beside the tests and is capped at 60 when they fail. The score and issues show on the approval card. If a review could not run, the card says **not run**.

## Results

Zero executed tests gives **INCONCLUSIVE**, never PASS. Healing can repair selectors and fixtures only, so real application defects stay as failing tests.

Generated tests are checked before they run: their imports must exist in your code, and they must use only plugins your repository has.`,
      },
      {
        slug: "copilot",
        title: "Copilot",
        summary: "Ask about the project, in the app or a separate window.",
        body: `## Chats

Open **Copilot** in a project, or use **Open in new window**. Pick an agent per chat. Chats are saved and can be renamed or deleted, and project memory is shared by all chats.

## Commands

| Command | Does |
|---|---|
| \`/scan\` | Starts a bug scan |
| \`/fix <finding id>\` | Fixes a finding on a branch |
| \`/gates\` | Shows gate status |
| \`/verify\` | Verifies the audit ledger |
| \`/feature <text>\` | Starts a feature |
| \`/docs <query>\` | Searches documents |

Agents can start workflows, but only people approve gates.`,
      },
    ],
};
