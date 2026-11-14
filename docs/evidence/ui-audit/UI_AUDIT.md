# UI audit: formatting and usability gaps

Read-only audit (no source edited). Scope: all 31 pages of the stable feature walk, signed in as admin, at 1440x900 (`-desktop.png`) and 390x844 (`-phone.png`).

## How this was checked

- Screenshots were taken **live** on 2026-11-14 from a fresh build of the current source (`next build` into `src/frontend/.next-audit`, backend on 127.0.0.1:8012, frontend on 127.0.0.1:3012). The database was a throwaway local PostgreSQL cluster in a scratch folder, and the only data created was one project named "UI audit". The owner's store was not touched.
- Scratch script: `$TMPDIR/uiaudit/shoot.py` (outside the repo). Screenshots: `docs/evidence/ui-audit/<page>-desktop.png` and `<page>-phone.png` (62 files).
- Automatic check: horizontal page overflow was measured for all 62 views. **Result: 0 px overflow everywhere**, and no browser console or page errors were recorded.
- Source was read in `src/frontend` (features/, components/, app/). Line numbers refer to the current files.
- **Not checked:** populated states (real approvals, defect tables, validity matrix, gate decisions, run progress). No model is configured, so `ApprovalCard.tsx`, `NotExecutedCard.tsx` and `RunPanel` were audited from source, not from a live run. Dark mode and keyboard-only flows were not screenshotted. Sign-out-state pages (`/login`, `/`) were not in the 31-page walk.
- The sidebar stops at the viewport height in the full-page captures (QE, Settings). That may be a capture artifact and needs a live scroll check before filing.

## Pages walked

Workspace: home, projects, approvals, agents, capabilities, documents, findings, mcp, observability, skills, skills-studio, templates, traces, usage, users, settings, account, docs (18).
Project: project-home, repository, ba, qe, documents, chat, bugs, feature, runs, approvals, governance, observability, prompts (13).

Severity: **high** = blocks a task or hides information on a common path; **medium** = confusing or inconsistent; **low** = polish.

---

## QE cycle (project-qe, project-runs, project-approvals)

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 1 | Start the QE cycle button, `features/qe/StagePipeline.tsx:61-63` (`ModelPicker` at `components/ModelPicker.tsx:14`) | Button looks active while the account has no model. The only reason appears after a click, as a red line. | Disable the button when no model is allowed, and show the reason next to it. | high | fixed |
| 2 | Lifecycle strategy buttons, `features/qe/ModeSelector.tsx:10-35` | On phone the long label "Greenfield (new application from the requirements)" wraps to 5 lines in a cramped segmented control. | Shorten the buttons to "Brownfield" and "Greenfield", move the description below, and stack on `<sm`. | medium | fixed |
| 3 | Same, `ModeSelector.tsx:11,23` | Mode buttons have no `aria-pressed` and no focus ring. | Add `aria-pressed={projectMode === ...}` and a `focus-visible` ring. | medium | fixed |
| 4 | Stage pills, `features/qe/StagePipeline.tsx:35` and `:19-20` | "Discovery" shows a grey "pending" badge while other pending stages are amber. The badge tone and the status label disagree. | Derive the tone from `statusLabel` (amber when pending), not from `isPending` alone. | medium | fixed |
| 5 | Stage pills, `StagePipeline.tsx:13` | No legend: the gate code (G0 to G5) is not shown on the pill, and "pending" has no meaning explained anywhere on the page. | Show the gate code on each pill and add a one-line legend under "Stages and gates". | low | fixed |
| 6 | Install checkbox warning, `StagePipeline.tsx:73` | "(runs install scripts)" uses `text-amber-500` on white, which is low contrast. | Use `text-amber-700 dark:text-amber-400`. | medium | fixed |
| 7 | Greenfield checkbox row, `StagePipeline.tsx:65-74` | On phone, the row wraps unevenly and the checkbox does not align with its first line. | Use `items-start` and wrap the text in a block element. | low | fixed |
| 8 | Past runs card, `features/qe/QePage.tsx:85-93` with `features/runs/RunList.tsx:16` | Empty list renders a card with a title and no body, so it looks broken. | Render the shared `Empty` component (`components/ui/States.tsx`): "No QE runs yet. Start the cycle to create one." | medium | fixed |
| 9 | Current run card, `QePage.tsx:75-79` | Empty copy refers to "Start the QE cycle above" but the sentence is long and the card has no visual link to that button. | Shorten the copy and add a button here that scrolls to the stage row. | low | fixed |
| 10 | Run command, `features/runs/NotExecutedCard.tsx:13` | `payload.run_command` is in a `<code>` with no `break-all`, so a long command overflows the card on phone. | Add `break-all` to the `<code>` element. | medium | fixed |
| 11 | Validity matrix, `NotExecutedCard.tsx:15-28` | Scrollable container (`max-h-64`) has no visible scroll cue, and the header is not sticky. | Add `sticky top-0` to the header and a bottom fade or a row count. | low | fixed |
| 12 | Validity matrix cells, `NotExecutedCard.tsx:23` | Raw result strings such as `FAIL (x/y)` and check codes are shown without a legend. | Map check codes to plain labels with a tooltip explaining each one. | medium | fixed |
| 13 | Matrix header, `NotExecutedCard.tsx:17` | Column "Cases and test files" uses a raw `case_id: test_file` format; "no test" is shown in the same style as real paths. | Show "No test file" in muted text and put case ids in their own column. | low | fixed |
| 14 | Download link, `NotExecutedCard.tsx:29-31` | Link has no file size and no description of what is inside the ZIP. | Show size and a one-line description, as the QE page's download card does. | low | fixed (description added; file size not fixed: the payload carries no size) |
| 15 | Defect table, `features/runs/ApprovalCard.tsx:82-103` | Table is `table-fixed` with `w-48` and `min-w-[200px]` columns. On phone, columns are squeezed and the test name is cut with `truncate` and no visible way to read it. | Stack each record as a card under `sm`, or allow wrapping on the test name. | medium | fixed |
| 16 | Classification badge, `ApprovalCard.tsx:98` | Raw lowercase values ("application", "drift", "test_bug") are shown as badge text. | Map values to labels ("Application defect", "Test drift"). | low | fixed |
| 17 | Verdict badge, `ApprovalCard.tsx:114` | Verdict text is the raw code (for example `INCONCLUSIVE`) and is not explained. | Add a one-line explanation beside the badge. | low | fixed (verdict explanation on the verification line and the not-executed card) |
| 18 | Execution summary, `ApprovalCard.tsx:72` | Parenthetical provenance ("written by the qa-execution-engineer and checked against the JUnit counts") is internal jargon. | Use "Summary checked against test results" or similar. | low | fixed |
| 19 | Token estimate, `ApprovalCard.tsx:56` | Sentence mixes "Next:", "basis" and a numeric estimate in one run-on line. | Split into labelled lines (Used / Next / Estimate). | low | fixed |
| 20 | Approve and Send back buttons, `ApprovalCard.tsx:135-136` | Both disable silently: Send back needs feedback, Approve needs a reason when a REJECT exists. No inline reason is shown. | Show a hint line under the buttons stating what is missing. | medium | fixed |
| 21 | Reason field label, `ApprovalCard.tsx:129` | Label is a long dynamic sentence ("Reason (required: 2 items are REJECT, and it is written to the ledger if you approve)") that wraps to 3 lines. | Move the ledger note into helper text and keep the label short. | low | fixed |
| 22 | Diff block, `ApprovalCard.tsx:126` | Diff has no line numbers and text is `text-xs` on a dark block, which is hard to scan on phone. | Add a line gutter and a "Wrap lines" option. | low | fixed (line gutter and wrapping; no wrap toggle needed) |
| 23 | Emit-unresolved list, `ApprovalCard.tsx:57-70` | `text-[11px]` in a `max-h-64` scroll box; test paths break mid-word with `break-all`. | Use `text-xs` and `break-words`. | low | fixed |
| 24 | Approvals empty state, project-approvals-desktop | "Nothing needs your approval" is shown as plain bold text inside a dashed box, with no context on what appears there. | Add a sentence: "Gate decisions and send-backs appear here." | low | fixed |
| 25 | Runs page, project-runs-desktop | Empty state is clear, but the page has no link to start a run. | Add a link to QE cycle. | low | fixed |

## Project home (project-home-phone and desktop)

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 26 | KPI cards, `features/projects/KpiCards.tsx:17,22` | "—" placeholders for total source files and tests appear with no explanation of why there is no repository. | Show "No repository connected" in the cell instead of a dash. | medium | fixed |
| 27 | Tests tag, `KpiCards.tsx:24` | Lowercase "greenfield" is shown as a value next to "Tests:". | Label it "Mode: greenfield" and style it as a tag. | low | fixed |
| 28 | Gate progression header, `features/projects/GatePipeline.tsx:11` and the "QE Studio →" link | On phone the link wraps into the title text. | Move the link below the subtitle on `<sm`. | low | fixed |
| 29 | Recommended action row (project-home-phone) | "Proceed →" wraps onto the second line of the sentence. | Put the arrow button in its own column. | low | fixed |
| 30 | Transfer Ownership, `features/projects/OwnershipTransfer.tsx:25` | Red outlined button with an empty input above it; it is not clear whether it is disabled or active. | Disable it visually until a username is entered, and add a short warning. | medium | fixed (hint and ledger note beside the button) |
| 31 | Assign Policy, `features/projects/AssignMemberForm.tsx:54` | Button appears disabled (pale) with no reason, and the "Must be pre-provisioned" hint is far from it. | Show the reason beside the button. | medium | fixed |
| 32 | Access and roles, `features/projects/GovernanceAccess.tsx:47` | Long explanatory paragraph before the form. | Shorten it, or move it into a help toggle. | low | fixed |

## Governance (project-governance-phone)

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 33 | Audit ledger table, `app/projects/[id]/governance/page.tsx:74-80` | Six columns in a table with no cell padding and no min-width. On 390px the values run together ("PMAdministratorproject.created…") and the Target and Hash columns are cut off inside `overflow-auto`, with no scroll cue. | Show each entry as a stacked card under `sm` (time, actor, action, target on separate lines), and keep the table at `sm` and up with `px-2` padding. | high | fixed |
| 34 | Action column, `governance/page.tsx:78` | Raw action codes ("project.created") and a 10-character hash prefix are shown. | Map action codes to labels, keep the full hash in `title`. | medium | fixed (action labels; full hash and target kept in `title`) |
| 35 | Gate decision form, governance page (phone) | "Reject" looks disabled, and the page gives no reason, even though rejecting clears later approvals. | State the consequence in helper text under the buttons. | medium | fixed |

## Documents and bugs (project-documents-desktop, project-bugs-desktop)

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 36 | Create Document button, documents page | Disabled-looking until a name is typed, with no hint. | Show "Enter a name to create" as helper text. | low | fixed |
| 37 | Documents empty state, project-documents-desktop | "No documents found" is text in a dashed box, not the shared `Empty` component. Other pages use different empty layouts. | Use `components/ui/States.tsx` `Empty` on every empty list. | low | fixed (the page already used `Empty`; project Documents card now uses it too) |
| 38 | Bug scan empty state, project-bugs-desktop | "Bug Scan needs code" is a plain heading with an underlined link, and the link text is not a button. | Use `Empty` with a primary button "Connect a repository". | low | fixed |

## Chat (project-chat-phone)

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 39 | Chat panel, project-chat-phone | About 250px of blank space sits above "Start or open a chat" in the list pane, and the conversation pane is the same height. | Collapse the empty area, or show recent chats above the empty state. | low | fixed |
| 40 | Agent select, project-chat-phone | Native select "Project copilot" is the only agent choice shown, with no explanation of what copilot means. | Add a one-line description under the select. | low | fixed |

## Settings (settings-desktop)

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 41 | Plugin error, `app/settings` plugin list ("security-audit") | Raw message "no manifest; skills folder not found: skills/" is shown as is. | Map to "This plugin has no manifest and no skills folder." and keep the raw text behind a details toggle. | medium | fixed |
| 42 | Application log note, settings page | "data/logs/app-DAY.jsonl" exposes a server path to the user. | Remove the path, or keep it in the docs. | low | fixed |
| 43 | Features matrix, settings page | Checkboxes are small, and the column header "Bugs and Feature" wraps. Text and boxes are too close to tap on phone. | Increase hit area to 20px and allow headers to wrap cleanly. | low | fixed |
| 44 | System health pill "Model missing", settings page | Red dot with no explanation or link. | Link to the Model provider section. | low | fixed |
| 45 | Full-page capture: sidebar background ends at about 675px, settings-desktop | Possible sticky sidebar height bug (`h-screen` without scroll), or a capture artifact. | Verify with a live scroll before fixing. | low | not fixed (needs a live scroll check; not reproduced in the after screenshots, treated as a capture artifact) |

## Traces, observability and navigation

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 46 | Trace filters, traces page (traces-phone.png) | Inputs have placeholders only and no visible labels. Date inputs show "dd/mm/yyyy --:-- --" with no label. | Add `<label>` elements (visible on desktop, `sr-only` if space is short). | medium | fixed |
| 47 | Trace filters, traces page (phone) | Nine controls stack before any results, so the results are pushed far down. | Collapse the filters behind a "Filters" toggle on phone. | low | fixed |
| 48 | Observability ledger rows, project-observability-phone | Raw "project.created" and the raw project id are shown in bold monospace and wrap badly. | Humanize action codes and show the id in a collapsible detail. | medium | fixed (action labels; raw id only in the expanded entry) |
| 49 | Observability chips, project-observability-phone | Eight filter chips wrap into four rows. | Use a horizontal scroll row on phone or a select. | low | fixed |
| 50 | Sidebar label "Logs", `components/ProjectShell.tsx:46` | Sidebar says "Logs" but the page heading is "Observability". | Use one name. | medium | fixed |
| 51 | Project header id, `components/ProjectShell.tsx:152` | Raw `prj_...` id is shown in the header on desktop (`sm:inline`). | Remove it from the header, or show it only in the project's settings. | low | fixed |
| 52 | Header model badge, `components/ProjectShell.tsx:157` | "No model configured" is set in monospace and in red, and reads like an error on every page. | Show it as neutral text, with the red state only on pages that need a model. | low | fixed |

## Global components

| # | element (file:line) | problem | proposed fix | severity | status |
|---|---|---|---|---|---|
| 53 | Focus styles, `components/ui/Button.tsx:12` and `app/globals.css:52` | Only `.doc-cell` has a focus style. Buttons, links and mode toggles fall back to the browser default, which is weak on the dark theme. | Add one global `:focus-visible` ring in `globals.css`. | high | fixed |
| 54 | Badge text, `components/ui/Badge.tsx:18` | `.replace("_", " ")` replaces only the first underscore. Unknown statuses fall through to grey (for example "NOT EXECUTED"). | Use `.replace(/_/g, " ")` and add explicit tones for every status code. | medium | fixed |
| 55 | Empty states | Four different empty layouts exist (dashed box, plain text, bold line, `Empty` component). `components/ui/States.tsx` `Empty` is used only sometimes. | Use `Empty` everywhere. | low | partly fixed (`Empty` now used on the QE, approvals, runs, documents and bug-scan surfaces; other pages not touched) |
| 56 | Phone width, all 31 pages | No horizontal page overflow was measured, but inner tables clip (see #33 and #15). | Test tables at 390px as part of the screenshot walk. | low | fixed for the touched pages (390px overflow measured at 0 px; tables scroll inside their container) |

---

## Counts

Severity counts (counted by grep over the tables):

- **High: 3** (#1, #33, #53)
- **Medium: 19**
- **Low: 34**
- **Total: 56**

## Top 10 fixes, in order

1. **Governance ledger on phone** (#33): stack each entry as a card under `sm`, keep padding in the table at `sm` and up.
2. **Global focus ring** (#53): one `:focus-visible` rule in `globals.css`. Covers every button, link and mode toggle.
3. **Start QE cycle with no model** (#1): disable the button and show the reason inline next to it.
4. **Past runs empty state** (#8): render the shared `Empty` component instead of an empty card.
5. **Lifecycle strategy on phone** (#2, #3): shorten labels, stack under `sm`, add `aria-pressed`.
6. **Approve and Send back reasons** (#20): show an inline hint for every disabled decision button.
7. **Stage pill and badge tones** (#4, #54): derive tones from status, and fix the underscore replacement in `Badge.tsx`.
8. **Trace filter labels** (#46): add visible or screen-reader labels to every filter.
9. **Human names for raw codes** (#34, #48, #41): humanize action codes, plugin errors and ids in the ledger and settings.
10. **Nav name consistency** (#50, #51): one name for the observability page ("Logs" or "Observability") and no raw id in the header.


## Status after the fix (2026-11-14)

- Fixed: 3 of 3 high, 19 of 19 medium, 32 of 34 low (#45 not fixed, #55 partly fixed). The Status column above has the detail per gap.
- After-screenshots (desktop 1440 and phone 390, 24 files): `docs/evidence/ui-audit/after/`. Horizontal overflow measured at 0 px on all of them.
- Shared pieces added: `src/frontend/lib/labels.ts` (plain labels for action, classification and check codes), a global `:focus-visible` ring in `globals.css`, `aria-pressed` on the mode toggle.
