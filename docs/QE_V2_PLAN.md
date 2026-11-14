# QE Cycle v2 plan: strict validity, brownfield download, greenfield build and run

Status: **draft for the owner's approval** (2026-11-14). Nothing below is built until the owner says yes.

## 1. Owner decisions (2026-11-14)

| Topic | Decision |
|---|---|
| Brownfield execution | Removed. Generated tests are downloaded as a zip and run by the team on its own systems |
| Brownfield validity before Gate 4 | The sandbox installs the dependencies, then only collects and compiles the tests (`pytest --collect-only`, `tsc --noEmit`, `javac`, `dotnet build`, `go vet`), plus the static checks. No test body runs. Gate 5 verdict is `NOT EXECUTED`, never `PASS` |
| Greenfield code | Either the team connects its new repository, or the platform builds the application from the BRD, PRD and stories and pushes it to a GitHub repository the user names |
| Where built code lands | A new branch `atlas/app-<run>` plus a pull request; never the default branch. Uses a GitHub credential saved in Settings |
| Greenfield stacks | Python FastAPI + React, Node/TypeScript (Next.js), Java Spring Boot, .NET, Go |
| Greenfield execution | Install, start the app on `127.0.0.1` in the sandbox, run unit, integration and E2E (Playwright, headless Chromium), with an evidence report in the UI |
| Azure for E2E | Custom container on the same B1 plan, image built by GitHub Actions on a Playwright base, stored in GitHub Container Registry (free). Azure cost unchanged |
| Requirement documents | Several uploads per project (BRD, PRD, user stories; `.md`, `.docx`, `.pdf`, `.txt`), read through a RAG pipeline: PostgreSQL pgvector plus keyword search, reranked |
| Models | For building this plan: Sonnet implements, Haiku does mechanical work (screenshot audits, checklists, doc drafts), Opus leads and reviews. The platform's runtime model stays the configured OpenAI-compatible model |
| UI | Full audit of every page at desktop and phone width; every gap listed, fixed and proved with a Playwright walk |

## 2. What "valid" means for a generated test

A test is **valid** only when every check below passes. Code runs each check; none is taken from a model's word.

| # | Check | Kind | Brownfield | Greenfield |
|---|---|---|---|---|
| V1 | Its case is linked to a plan scenario at the same level, and the coverage auditor says `COVERS` | inferential sensor, recorded | yes | yes |
| V2 | Its case's expected result can be derived from the requirement's quote. A case whose oracle is not in the quote is refused | computational: quote and oracle match, then reviewer | yes | yes |
| V3 | The file parses, then collects or compiles in the sandbox with the repository's own dependencies | computational | yes | yes |
| V4 | Every import resolves, and every symbol it calls exists in the repository (`emit.check`, signatures) | computational | yes | yes |
| V5 | Assertion integrity: at least one assertion per test; no `assert True`, no tautology, no removed assertion, no skip; the assertion checks the case's expected result | computational (AST) | yes | yes |
| V6 | Traceability: the test carries its case id; the plugin's `check-gate --gate 4` passes (manifest, markers, code review, code audit) | computational, plugin | yes | yes |
| V7 | It runs and passes against the real application, or it fails on a real defect that the reviewer confirms from the code | computational, then inferential | no (not executed) | yes |
| V8 | Mutation smoke: a seeded fault in the code under test makes it fail | computational | no | yes, sampled per requirement |

Invalid tests are never shipped as valid. The zip has `tests/` (valid) and `needs-review/` (with the failed check and fix
for each), plus `VALIDATION.md` and the plugin's `coverage-map.md`. Gate 4 shows the counts by check.

## 2a. Carry-forward hook (traceability between every step)

The engine runs one hook around **every** stage of both flows: before the stage starts and after it ends. It is code,
not a model. A failed check blocks the run from going on. Each check is written to the ledger with the stage and the
hashes.

| When | What it checks | On failure |
|---|---|---|
| Before a stage | Its inputs match the snapshot taken when the last gate was approved: same ids, same SHA-256 per item (requirement: id, statement, priority, file, line, quote; scenario: id, level, requirement ids; case: id, requirement id, scenario ids, steps, expected result, test data; test: path, case ids, content hash). | The stage does not start. The card names each changed or missing item: "REQ-004 quote changed after Gate 1". |
| After a stage | **Carried exactly:** every upstream item the stage copies forward keeps its fields byte for byte. Examples: the plan's requirement ids, a case's requirement and quote, a test's case id and expected result. | The stage's output is refused. The agent is asked once to regenerate from the unchanged inputs, with the list of what it altered. |
| After a stage | **Complete:** every upstream id is covered downstream (every requirement in the plan, every scenario has a case, every case has a test), or it is listed with a written reason, such as the case budget or a level skipped with its reason. | Same: regenerate once, then the stage fails with the list. It never moves on silently. |
| After a stage | **No invention:** downstream items reference only ids that exist upstream. Copied text (quotes, expected results) appears verbatim in its source. | Same. |
| At each gate | The gate card shows the trace table: upstream count, carried, changed, dropped with reason, new. Every item is clickable to its source. | A gate with an unexplained change cannot be approved. |

Snapshots: `docs/qe/<app>/trace/<stage>.json` (ids plus hashes), and the hook's verdict is kept next to them. A person's
send-back at a gate is the only way an approved upstream item may change, and the next gate's snapshot records it.

## 3. Brownfield flow (v2)

```
intake G0 -> discover -> requirements G1 -> plan G2 -> design + data G3 -> generate -> validate G4 -> trace + sign G5
```

- **Removed:** Prepare, Execute and Heal. The QE page no longer shows the Install dependencies switch for brownfield.
  Validate installs the dependencies only to collect and compile; that runs the repository's installers, so the Gate 0
  card says so and the person approves it there.
- **Validate (new):** runs V3 to V6. Each failure goes back to the automation engineer once, with the message (what,
  where, how to fix). What still fails goes to `needs-review/`.
- **Gate 5:**
  - The verdict is `NOT EXECUTED`.
  - The Gate 5 card shows the traceability matrix, the valid and invalid counts and the plugin Gate 5 check.
  - It offers the zip download and the run command for each framework.
- **Plan levels:** unit and integration are required. E2E is planned only when the repository has a UI or entry point;
  otherwise the plan needs a written reason.

## 4. Greenfield flow (v2)

```
intake G0 (documents, target repo) -> read documents (RAG) -> requirements G1 -> plan G2 -> design + data G3
  -> build app (or connect repo) GA -> generate -> validate G4 -> execute <-> heal -> evidence + sign G5
```

- **Documents:** several uploads. Each one is parsed to text with structure kept (headings, tables, lists, page and line).
  The text is saved under `docs/sources/` in the workspace, so the plugin's quote check works on greenfield too.
- **Requirements:** every requirement cites document, section and an exact quote. Code checks the quote against the saved
  text, and the plugin's Gate 1 check runs as for brownfield.
- **Build app (Gate A, new):** only when the user asks the platform to build.
  - A **solution architect** agent picks the stack template and the module layout, then writes an architecture note.
    The person approves it at Gate A.
  - The **feature engineer** builds the app in a worktree, feature by feature. After each feature it runs that stack's
    build, lint and the app's own smoke start. At most 2 fix rounds per feature.
  - The code is pushed to `atlas/app-<run>` in the user's repository and a pull request is opened.
- **Execute:** install, start the app on a free loopback port (and its database if the template has one), run unit, then
  integration, then E2E with Playwright. Screenshots, trace and video are kept per E2E test.
- **Heal:** selectors and fixtures only. A real defect stays a failing test (unchanged rule).
- **Evidence report (Gate 5):**
  - An HTML page in the UI and in the zip.
  - Content: the verdict, every requirement to its cases to its tests to its results, E2E screenshots, mutation scores,
    and the failure analysis.
  - Zero executed tests is `INCONCLUSIVE`.

## 5. RAG pipeline (greenfield documents)

| Step | How |
|---|---|
| Parse | `.md`, `.txt` as is; `.docx` through `python-docx` (installed); `.pdf` through `pypdf` (new dependency, BSD) with page numbers |
| Chunk | By heading, then by paragraph to about 800 tokens with 15% overlap. Each chunk keeps document, version, section path, page and line range |
| Index | PostgreSQL `pgvector` (Azure Database for PostgreSQL allows the `vector` extension) plus PostgreSQL full-text search |
| Embed | The configured OpenAI-compatible endpoint's embedding model. If it has none, keyword search only, and the page says so |
| Retrieve | Hybrid: keyword and vector scores merged (reciprocal rank fusion), top 20; then reranked by the model to top 8 per question |
| Ground | Agents get chunks with their citations. Every requirement quote is checked verbatim against the chunk text on disk; a quote not found is dropped |
| Evaluate | An eval set of questions with known answers over a sample BRD: recall@8, citation accuracy, no-answer when the documents do not say |

## 6. Agents

| Agent | New or existing | Job |
|---|---|---|
| requirements-analyst | existing, extended | greenfield: requirements from retrieved chunks with citations |
| principal-test-architect | existing | plan; E2E rule above |
| test-design-architect | existing | cases; oracle must come from the quote (V2) |
| confidence-reviewer | existing | per-case and per-test scores |
| coverage-auditor | existing (added at G3) | design audit, and now code audit for Gate 4 (V1, V6) |
| test-automation-engineer | existing | tests; fixes from Validate messages |
| solution-architect | **new** | greenfield stack, layout, architecture note for Gate A |
| feature-engineer | existing | builds the greenfield app feature by feature |
| defect-diagnostician | existing | greenfield heal: selectors and fixtures only |
| qa-execution-engineer | existing | greenfield execution summary, checked against JUnit counts |
| document-analyst | **new** | answers retrieval questions about the uploaded documents with citations; says "not in the documents" when they do not say |

## 7. UI

1. A Haiku subagent screenshots every page at 1440 px and 390 px. It lists each gap with page, element and fix:
   spacing, alignment, overflow, empty states, loading states, error text, table wrapping, contrast and focus order.
2. A Sonnet subagent fixes them, QE Cycle first: stage pipeline, gate cards, documents, the new evidence report.
3. A Playwright walk with screenshots proves the result, at both widths.

## 8. Azure

- **Image:** a custom container on the existing B1 plan. GitHub Actions builds it from `mcr.microsoft.com/playwright/python`
  and adds Node 22, JDK 21, .NET 8 and Go. It is pushed to `ghcr.io/sarveshtalele/agentic-qe` and App Service pulls it.
- **Database:** the existing PostgreSQL Flexible Server with the `vector` extension allow-listed.
- **Cost:** the table in `docs/AZURE_DEPLOYMENT_GUIDE.md` is updated. The target is unchanged, under $25 a month.
- **Load:** one greenfield run at a time, which the backend enforces.

## 8a. Fixes from the live run of 2026-11-14 18:59

| Finding | Fix |
|---|---|
| After a Gate 4 send-back, the first attempt's files stayed in the worktree: 132 tests ran for 80 cases, and the old ones failed with `KeyError` on fixtures that no longer existed | Generate removes this run's uncommitted files under `tests/agentic_qe/` before it regenerates (`git.untracked`) |
| The two reviewers disagreed: the confidence reviewer judged 1 of 80 cases REJECT, while the auditor said 27 PARTIAL or MISSES | A case the auditor says MISSES is redesigned once from the auditor's reason, then reviewed and audited again. If it still misses, its record becomes REJECT, so approving it needs a person's reason |
| The case budget gave no case to planned lower-priority requirements, so their plan scenarios had none and the plugin's Gate 3 check failed | Every requirement the plan lists gets at least one case |
| The execution agent said 8 tests when the report had 132 (refused by code) | Brownfield execution is removed in step 2; greenfield keeps the code check |
| Generated files failed at collection (`ImportError`) and were classed as environment | Step 1's collect check (V3) refuses them before Gate 4 |

## 8b. Findings from the live runs of 2026-11-14 20:30 to 20:51

| Finding | Fix |
|---|---|
| V3 failed every test: the run's environment was made in Prepare, after Gate 4 | Generate installs the dependencies before the validity checks |
| The carry hook excused requirements with no case whenever the budget notice was on | Only `left_out_requirements` (the budget) excuses a requirement without a case |
| The hook then stopped a run where Design gave REQ-023 and REQ-027 no case | Correct block; the redesign of auditor MISSES then cut MISSES from 16 to 0 in the next run |
| 15 tests failed collection: relative imports beyond the top-level package | The generation prompt now carries the repository's own test import style and says tests/agentic_qe is not a package |
| None of the 30 "defects" was an application defect, all were test bugs: a sync httpx client on an async transport, a missing await, and calculator names that do not exist in the repository | An error raised by the test's own code is `TEST_BUG` (a test problem, never healed, never a defect). The prompt names the async client rule and forbids inventing input values. **Not yet caught: an invented input value that leads to a clean assertion failure.** That needs V2b, below |

**V2b (planned with step 3):** input values in Positive cases must appear in the repository (a registry name, route, key or enum)
or in the requirement quote. Without execution, brownfield cannot see these failures, so this static check is the only
guard.

## 9. Order, models and evidence

Each step: Sonnet implements, Opus reviews against the brief, Sonnet fixes, then the full suite and CI must be green before
the commit. Live runs use the real model and real repositories.

| # | Step | Implementer | Done when |
|---|---|---|---|
| 0 | Carry-forward hook (section 2a): snapshots, before and after checks, regenerate once, trace table on every gate card, ledger entries | Sonnet | seeded changes are each blocked, with their names on the card, in tests: a requirement quote edited in the plan, a case's expected result altered in a test, a requirement dropped without a reason, an invented case id. **Status: done offline, 2026-11-14** (`src/backend/qe/carry.py`, `tests/test_carry.py`; not yet run on a live model, not committed) |
| 1 | Validity checks V3 to V6 and the zip with `tests/`, `needs-review/`, `VALIDATION.md` | Sonnet | seeded bad tests (no assertion, `assert True`, wrong import, wrong symbol, missing case id) each refused, in tests **Status: done offline, 2026-11-14** (`src/backend/qe/validity/`, `generate/validate.py`, `api/run_tests.py`, `tests/test_validity.py`, `tests/test_api_validity.py`; not yet run on a live model, not committed) |
| 2 | Brownfield v2 flow: Validate stage, Execute, Prepare and Heal removed for brownfield, Gate 5 `NOT EXECUTED`, plugin Gate 4 and 5 checks | Sonnet | live run on personal-finance-mcp to Gate 5 with the zip, every stage at or under 180 s |
| 3 | V2 oracle check in Design, and V1 code audit | Sonnet | seeded case with an invented expected result refused |
| 4 | Documents: multi-upload, parse, chunk, pgvector plus keyword, rerank, citation check, RAG eval | Sonnet | RAG eval recall@8 at least 0.9 and citation accuracy 1.0 on the sample BRD |
| 5 | Greenfield requirements, plan and design on RAG, plugin Gates 1 to 3 | Sonnet | live run from an uploaded BRD to Gate 3 |
| 6 | Stack templates (5) and the solution-architect agent, Gate A | Sonnet | each template builds and starts in the sandbox, in tests |
| 7 | App build, branch and PR push | Sonnet | live build of a small BRD app (FastAPI + React) pushed as a PR to a test repo the owner names |
| 8 | Greenfield execute, heal, mutation smoke, evidence report | Sonnet | live greenfield run to Gate 5 with E2E screenshots in the report |
| 9 | UI audit and fixes | Haiku (audit), Sonnet (fixes) | Playwright walk at two widths, every listed gap closed |
| 10 | Azure container (GHCR), pgvector, guide | Sonnet | `dev.py azure-local --check` and a container start with Chromium, locally |
| 11 | Docs and README | Sonnet subagent | every doc matches the code; links checked |

Pinned limits (`ponytail:`):
- One greenfield run at a time.
- Mutation smoke is sampled per requirement, not full mutation testing.
- The reranker is the same chat model, not a dedicated cross-encoder.
