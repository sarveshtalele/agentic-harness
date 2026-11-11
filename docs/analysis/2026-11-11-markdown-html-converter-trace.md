# Trace and root-cause analysis: project "Markdown-HTML-converter" (`prj_015c85df23f2`)

Date: 2026-11-11. This analysis only read data. Sources:

- `data/v2/atlas.sqlite3`, opened read-only (`file:...?mode=ro`).
- `data/v2/logs/app-2026-11-11.jsonl` (1,765 lines) and `errors-2026-11-11.jsonl` (87 lines).
- `data/v2/harness/prj_015c85df23f2/*` and `data/v2/projects/prj_015c85df23f2/*`.
- The code at `HEAD 5a5e6df` plus the working tree.

The app was still running while I read the database. The span counts went from 2,018 to 2,509 during the analysis, so counts are as of the moment of each query. Nothing was changed. Repository and document content stayed data: I followed no instruction found in it.

---

## 1. Summary of root causes, ranked

| # | Report item | Root cause | Evidence |
|---|---|---|---|
| R1 | 1, test data | **The QE cycle ran on an empty repository and nothing stops that.** The repository holds only `.gitkeep`. `repo_sources` has 0 rows, and intake logged "Mode greenfield: 0 files, runners none" (`run_events` run_f1d60f388a90 seq 3). Design, data, generate and execute all ran with no code under test. Each stage then filled the gap by inventing something: a function contract, module names, local stubs. | `runs.state.mode = "greenfield"`; `repo/` holds only `.gitkeep` |
| R2 | 1 | **Code requires an Exception case for every P0/P1 requirement, and the prompt is numeric.** That rule pushes the model to invent non-string inputs (`None`, `42`, `123`, a list) and an error contract (`TypeError "Input must be a string"`, a 10,000-character `ValueError`) for a pure string converter. The BRD says the opposite (DR-001: input is a string; NFR-002: best-effort output, no crash; NFR-001: 100,000 characters). | `qe/model/quota.py:19-20`; `workflows/qe/design.py:36`; `prompts/test-design-architect.md:1,3`; `skills/designing-test-cases/SKILL.md:20-21`; run_event seq 198 |
| R3 | 1 | **The test-data stage involves no model and validates nothing.** `qe/test_data.py:_kinds` tags datasets with a keyword regex. The word "negative" in "(negative)" or a `Negative (Boundary)` type adds `boundary.number`, whatever the input type. The generic `boundary` payloads (for example `"A"*1024`) are pasted in, unused by any test. The case's free-text `test_data` is copied verbatim. | `qe/test_data.py:26,77-78,103`; `workflows/qe/data.py:12-14`; doc `doc_1fde01a4e5fe` |
| R4 | 1, 2 | **No check compares a case's data or oracle with the requirement.** `TestCase.test_data` is a free `str` and `oracle` is a self-declared label (`qe/model/cases.py:18,21`). The confidence review did flag all 40 cases REJECT. Approval needs only a non-empty reason, and the reason given was `"a"`. | `maf/engine/__init__.py:80`; ledger seq 118 |
| R5 | 1, verdict | **Generated tests define their own subject under test, and the static checks accept them.** The "not installed" finding tells the model to "use only the standard library", which leads it to write stubs. All 3 passing tests test a local stub, and the verdict counts them as real coverage. | `qe/emit/python.py:151`; `workflows/qe/generate/files.py:32-48`; `workflows/qe/trace.py:30` |
| R6 | 4, `***` | **The admin's name was redacted as a secret, and the UI reads the name back from the redacted text.** The committed `register_secret` masks any registered secret of 4 or more characters as a substring. A registered secret equal to the text `admin` turned every "admin" into `***`. `add_event` stores `redact("Approved by admin")`, and `api/runs.py:66` parses `decided_by` back out of that message. | `core/security.py@HEAD:121`; `maf/engine/run_context.py:60`; `maf/engine/stages.py:76`; `api/runs.py:66`; `RunPanel.tsx:131` |
| R7 | 3, approval | **Two approval systems, and the chat shows and records only one, briefly.** MAF did raise tool-approval interrupts for `create_skill` (twice) and `start_workflow`, and each was answered `approved` within 3 to 24 s. The answer and the card are stored nowhere, and the transcript duplicates the user turn. The workflow's gate approvals appear only on the project Approvals page, never in chat. | `agui.py:84-89,126-130`; `Conversation.tsx:74-80`; `RunStatus.tsx:49`; tool_calls 13, 20, 24 |
| R8 | 2, logs | **Logs cannot be joined.** No `run_id`, `trace_id` or `thread_id` on log lines. `agent_calls` has no stage, trace or thread. Model input and output are not stored. Chat and workflow traces are not linked. The tool-approval lifecycle is not logged. | §7 |

---

## 2. Trace timeline (UTC)

### Project and source

- **`projects`.** `prj_015c85df23f2`, name "Markdown-HTML-converter", description "create Markdown to HTML converter skill". Owner `admin`. Created 2026-11-11T06:22:55.
- **Repository source.** None. `repo_sources` has 0 rows. `data/v2/projects/prj_015c85df23f2/repo/` holds only `.gitkeep` and `.git`. Gate 0 summary: "Mode: greenfield. Source: no repository. Files: 0. Languages: none." (approval `cf0bb2f4-…`, payload `analysis.total_files = 0`).
- **`sources`.** 0 rows. The BA run used no source documents (run_d5d37df5f1d2, event seq 9: "0 source documents").
- **Model.** `settings.llm_model = deepseek-v4-flash-global`, through a LiteLLM proxy. Every `agent_calls` row uses this model.

### Event timeline

| Time | What | Ids |
|---|---|---|
| 06:16:27 | admin signs in | `auth_events` id 1; `sessions` token for user `admin` |
| 06:24:26 | first BA run refused: 412 AQE-MODEL-006, "No model configured" | `req_ad7962a578fc`, `err_3b3363243860` |
| 06:25:08–06:25:29 | LLM settings saved and tested | `PUT /api/settings/llm`, `POST /api/models` |
| **06:26:22** | **BA run** `run_d5d37df5f1d2` (workflow `ba`, user `admin`), input `{"brief":"Create Markdown to HTML converter skill ","template_id":"builtin_brd"}` | |
| 06:26:22 → 06:26:28 | Gate 0 created and approved. The admin typed `admin` as the feedback | approval `cf0bb2f4-0728-4daa-a419-65cc3fa47605`, `decided_by=admin`, `feedback=admin`; ledger seq 4 stores the reason as `"***"` |
| 06:26:38 | BRD v1 drafted (business-analyst) | `doc_1c0c877362d0` v1, sha `161c5449…`, `prompt_ref business-analyst@v1:a9a1dc6be214+skills:c35a8c4f9409` |
| 06:26:45 | review 40, REJECTED → redraft | seq 20 |
| 06:27:01 / 06:27:07 | BRD v2, review 57, REJECTED | `doc_1c0c877362d0` v2, sha `7f232f62…`; seq 31 |
| 06:27:16 | Gherkin "valid: 29 scenarios, 87 steps" | `doc_6e447f8c4675` v1; seq 37 |
| 06:27:42 | admin creates Skill Studio plan from BRD v2 | `spl_96abff2b0075` (source `doc_1c0c877362d0@v2`) |
| 06:28:38 | admin approves that plan | ledger seq 17 `skill.plan.approved` |
| 06:29:08 | Skill generation fails 502: "SKILL.md must start with YAML frontmatter" | `req_68a12c352c80`, `err_e2476efb2970`, reply file `data/v2/skill_drafts/failures/rep_145fb3c3fd45.txt` |
| 06:29:26/27 | Gate 1 approved (review 57 REJECTED); BA run completed (3 min 5 s, 19,091 in / 7,745 out tokens) | approval `a39ac5b7-…`; ledger seq 21 and 23 (G1 recorded twice: once by the approval, once "Approved via document md-html-skill (v2)") |
| 06:34:30–06:35:12 | agent evals (`prj_agent_evals`) | `POST /api/agents/evals/run-all` |
| **06:36:13** | **harness chat thread** created | `thr_99acf774e3d2` (agent `harness`) |
| 06:36:47 | user: "create skill and rectify if already created … and test it" | chat seq 1, id `3ffc69d4-…`; `req_8e5753e4df95`; trace `e9ce1660…` |
| 06:36:51–06:37:05 | harness: mode_get, list_documents×4, read_document×3, find_tools, file_memory_ls, load_tools(create_skill), then calls **`create_skill`** → MAF approval interrupt; the turn ends | tool_calls 1–12; agent_calls 52–57 |
| **06:37:11** | **resume** request; the chat stores the same user message again | chat seq 3 (same id `3ffc69d4-…`); `req_f3b406705cb0`; trace `e96251e1…` |
| 06:37:11–06:37:18 | `create_skill` executes (7,585 ms) → draft plan `spl_0ebcbd9403f1` | tool_calls 13 |
| 06:37:49 | user types "approve"; the harness says to approve in Skill Studio | chat seq 5–6; `req_69c413f5ee0c` |
| 06:38:06 | user: "i ahve already approved it". The harness calls project_status, which shows `decided_by:"***"` for G0 and G1, then calls **`create_skill`** again → interrupt | chat seq 7–8; tool_calls 14–19 |
| **06:38:43** | resume; `create_skill` runs → **second** draft `spl_acf593aaa8ca` | chat seq 9 (duplicate); tool_calls 20; trace `6103c759…` |
| 06:39:21 | user: "apporved fomr studio". **No Studio approval request exists for either harness plan**: no `POST …/approve` for them in the app log, and both are `skill_plans.status='draft'`. The harness answers "Great, the plan was approved" | chat seq 11–12; tool_calls 21–23 |
| 06:39:38 | harness calls **`start_workflow`**(qe, "Markdown to HTML Converter - Full QE") → interrupt | agent_call 74 |
| **06:39:41** | resume; `start_workflow` runs (9 ms) → **QE run `run_f1d60f388a90`** | chat seq 13 (duplicate); tool_calls 24, trace `157eb647…`; workflow trace `de1ac228…` (not linked) |
| 06:39:41 | QE intake: Gate 0 already approved, so it is skipped (`shared/intake.py:19-20`) | seq 1–4 |
| 06:39:47–06:39:51 | discovery: first answer cited `docker-compose.yml`, `package.json` and `pyproject.toml`, which do not exist. It was sent back, then saved | seq 12; `doc_98a3ee4c42d9` |
| 06:39:51–06:43:05 | requirements: one requirements-analyst call taking **189,522 ms**, giving 15 requirements; review 75, REVISE | `doc_107af13cbee3`; seq 24, 27 |
| 06:43:05 | **Gate 1 appears on the project Approvals page, not in chat** | approval `cb1b278f-bf5d-40f5-91e9-1f890c138fd0` |
| 07:38:32 | G1 approved by admin (the run waited **55 min 27 s**) | ledger seq 51 |
| 07:38:44 / 07:39:18 | test plan (score 100, review 85, REVISE); G2 approved | `doc_e5ed18321a76`; approval `d9284e9a-…` |
| 07:39:18–07:40:56 | design: 44 test-design-architect calls and 21 confidence-reviewer calls; 40 cases, **0 approved, 40 REJECT**; 199,476 tokens | seq 175–206; `doc_64223585b51b` |
| 07:40:55, 07:40:58 | admin decides G0 twice from the Governance page (reasons `""` and `"as"`, no run_id). **Why: not found** | `req_d1d2caa7d69f`, `req_158e73664f9a`; ledger seq 111, 116 |
| 07:40:56 | data stage: "Test data built for 40 cases from 1 shared datasets (boundary); no model call" | seq 209; `doc_1fde01a4e5fe` (author `system`, prompt_ref empty) |
| 07:41:46 | G3 approved with reason `"a"` and all 40 REJECT items accepted | approval `02a6d5d3-…`; ledger seq 117–118 |
| 07:41:46–07:43:20 | generate: 58 test-automation-engineer calls; 40 files failed the static checks, 34 still failed after one round; worktree branch `atlas/qe-388a90` | seq 215–408; `doc_2498a1ce12fa` |
| 07:43:39 | G4 approved, reason "approved", REJECT items TC-APP-008 and TC-APP-020 accepted; commit `bd0dd08` | ledger seq 185–186 |
| 07:43:39–07:43:43 | prepare, execute: pytest **3 passed, 37 failed** (31 errors and 6 failures in the JUnit file) | seq 417; `worktrees/run_f1d60f388a90-results/pytest-1794383019538.xml` |
| 07:43:43 | greenfield → heal skipped → trace: verdict FAIL, 20 % coverage | seq 422–425; `doc_5aee5825af6f`, `doc_f385a4f896d7` |
| 07:43:46 → 07:44:04 | release doc; **G5 approved on verdict FAIL** (reason "done"); run completed (64 min 23 s, 408,289 in / 74,553 out tokens) | `doc_156e8df87de0`; approval `cf97130a-…`; ledger seq 193 |

### Runs

| Run | Workflow | Status | Start → end | Tokens in/out | Calls | run_failures |
|---|---|---|---|---|---|---|
| `run_d5d37df5f1d2` | ba | completed | 06:26:22 → 06:29:27 | 19,091 / 7,745 | 5 (business-analyst 3, confidence-reviewer 2) | 0 |
| `run_f1d60f388a90` | qe | completed | 06:39:41 → 07:44:04 | 408,289 / 74,553 | 129 | 0 (`run_failures` table is empty) |

### Stage durations

These come from the `spans` table, kind `internal`, name `stage …`, for run_f1d60f388a90:

| Stage | Duration | Stage | Duration |
|---|---|---|---|
| intake | 5 ms | generate | 94,226 ms |
| discover | 10,245 ms | prepare | 187 ms |
| requirements | 193,872 ms | execute | 3,563 ms |
| plan | 11,775 ms | trace | 26 ms |
| design | 97,925 ms | sign | 3,373 ms |
| data | 15 ms | | |

### Agent calls

| Run | Agent | Calls | Tokens in / out | Latency total | prompt_ref |
|---|---|---|---|---|---|
| qe | repo-intelligence-analyst | 2 | 2,968 / 755 | 6.8 s | `@v1:a1e847d3fdc7+skills:07e760ba44b9` |
| qe | requirements-analyst | 1 | 5,526 / 2,049 | **189.5 s** | `@v1:4a50c0c9ea8a+skills:ad8703e96008` |
| qe | principal-test-architect | 1 | 2,998 / 1,206 | 6.8 s | `@v1:f30b80cfba85+skills:041d4d8af72c` |
| qe | test-design-architect | 44 | 137,240 / 16,357 | 155 s | `@v1:0d7e68b47b84+skills:7f27fdea7e23` |
| qe | confidence-reviewer | 21 + 1 | 100,567 / 33,505 | 230 s | `@v1:701dcc771c0e` (+ `skills:3d3059704392` for release) |
| qe | test-automation-engineer | 58 | 155,895 / 20,561 | 221 s | `@v1:8bd7bcd7f9fe+skills:d38ca2471e4a` |
| qe | qa-execution-engineer | 1 | 3,095 / 120 | 3.2 s | `@v1:9a977c25f813+skills:afe7455e1e8e` |
| chat | harness | 22 (ids 52–76) | 235,644 / 3,386 | 84 s | `harness@v2:81b2892284f4` |
| studio | skill-creator | 7 | 35,640 / 10,018 | 55 s | `skill-creator@v1:aca2d48e5b0b` |

All `status=ok`, `error=''`. No row in `agent_calls` has an error.

### Other tables

- **Tool calls.** `tool_calls` has 24 rows, all from the harness in chat, `run_id` NULL, all ok. The risky ones are `create_skill` (ids 13 and 20, 7.6 s and 6.4 s) and `start_workflow` (id 24, 9 ms).
- **Ledger.** 236 rows in all for the database; the project's highest seq is 194. All gate actors are `admin`. There is **no ledger row for any harness tool approval**; only `chat.reply` (7) and `harness.tools_loaded` (4) are recorded.
- **Documents.** 11 documents and 12 versions. `test_data`, `test_code`, `defect_report`, `traceability` and `release` stay `draft` after G3 to G5, because `core/gates.py:76` approves only discovery, brd/requirements, test_plan, and test_cases/gherkin.
- **Chat.** One thread, `thr_99acf774e3d2` (harness), with 14 messages: 7 user rows, of which 3 duplicate an earlier row's id, and 7 assistant rows. The MAF snapshot is in `harness_snapshots` (scope `prj_015c85df23f2/admin`, 77 KB), plus `data/v2/harness/prj_015c85df23f2/history/~session-….jsonl` (826 KB) and the loaded tools `["create_skill","project_status","start_workflow"]`.

---

## 3. B: why the test data is poor

### 3.1 Which stage produced what

| Artefact | Stage | Producer | Prompt and skill | Validator |
|---|---|---|---|---|
| Case `test_data` text ("None", "42", "input = 123 (integer)", "A Python list …") | **design** (`workflows/qe/design.py:41`) | model `test-design-architect`, `deepseek-v4-flash-global` | `prompts/test-design-architect.md` v1 (sha `0d7e68b4…`) + skill `designing-test-cases` 1.4.0 | `TestCase` pydantic only (`qe/model/cases.py:9-29`) and `coverage_gaps` (`qe/model/quota.py:8-21`) |
| `datasets.boundary.*` (including `maxLength1024 = "A"*1024`) and the `uses` tags (`boundary.number` …) | **data** (`workflows/qe/data.py:12`) | **code**, `qe/test_data.py:build_fixtures`. No model call; author `system`, empty `prompt_ref` (doc_1fde01a4e5fe v1) | skill `generating-test-data` (ported from `synthesize-data.ts`) | none |

So the strange inputs are **model output from the design stage**, copied verbatim. The `boundary.number` tags and the 1024-character "A" string are **deterministic code**, not the model.

### 3.2 The model's input

The model input is not stored (see gap G1). It is reconstructed here from `design.py:41`, `design.py:36` and `runs.state`. The system part was `test-design-architect@v1:0d7e68b47b84` plus `skills:7f27fdea7e23`. The user message:

```
Design test cases for only these requirements.
REQUIREMENTS:
[{"id":"REQ-002","title":"Convert heading with 6 hashes to H6",
  "statement":"When the actor provides Markdown input starting with six hashes ... returns HTML output containing <h6>...",
  "type":"functional","priority":"P1","tier":"specified","actor":"customer","file":"","line":0,
  "quote":"FR-001: The system shall convert Markdown heading text preceded by 1-6 `#` symbols to ... <h1> through <h6> tags."}, ...]
CASE QUOTA, at most this many cases for each requirement (for 4: 1 Positive, 2 Negative, 1 Exception; ...):
REQ-001: 4, REQ-002: 4, ...
PLAN: {"strategy":"No repository detected. Using PyTest ... Integration tests cover ... boundary conditions (auth, I/O) ..."}
```

Every requirement has `file:""` and `line:0`. No code exists to send; `_design_evidence` had nothing to cite.

### 3.3 The model's output

From `doc_64223585b51b` v1 data:

| Case | Type | test_data | expected_result | oracle |
|---|---|---|---|---|
| TC-APP-004 | Exception | `input = null` | TypeError "Input must be a string" | specified |
| TC-APP-008 | Exception | `input = 123 (integer)` | TypeError "Input must be a string" … "Since no source is provided, the oracle is derived from the NFR" | derived |
| TC-APP-012 | Exception | 5 asterisks + 'A'×9996 … | ValueError "Input exceeds maximum length of 10000 characters" | **specified** |
| TC-APP-020 | Exception | `None` | TypeError; the precondition says "source code … is not available, so assume a typical implementation" | derived |
| TC-APP-024 | Exception | `42` | TypeError "Input must be a string" | **specified** |
| TC-APP-032 | Exception | "A Python list containing one element" | TypeError | metamorphic |

The case types split exactly 10 Positive, 10 Negative, 10 "Negative (Boundary)" and 10 Exception: 4 per requirement for 10 P1 requirements. That is the quota shape.

### 3.4 What the BRD actually says

From `doc_1c0c877362d0` v2:

- **DR-001:** "Input must be a plain string containing Markdown syntax."
- **NFR-002:** "The system shall handle invalid Markdown without crashing, returning best-effort output."
- **NFR-001:** inputs up to 100,000 characters.

No requirement defines a `TypeError`, an error message, or a 10,000-character limit. The "specified" oracles on TC-APP-012 and TC-APP-024 are false labels.

### 3.5 Reasons, each with evidence

1. **The prompt asks for something different in two places.**
   - `prompts/test-design-architect.md:1` says "an Exception case **when failure handling exists**".
   - Line 3 says "produce at least 1 Positive, 2 Negative …, and **1 Exception**".
   - Line 3 also says "Use boundary values: minimum, maximum, 0, just above, just below". These are numeric boundaries, with nothing about strings or Markdown.
   - The skill `skills/designing-test-cases/SKILL.md:20` says "Exception (1): Error handling under service failures or system exceptions". A pure function has none.
2. **Code enforces the Exception case.** `qe/model/quota.py:19-20` marks a requirement with no Exception case as a gap. `design.py:90-97` then re-designs. Run event seq 198 shows it: "Design checks found gaps ['REQ-013: no Exception case', 'REQ-015: no Exception case'] … revising". The quota text `design.py:36` and `quota.py:107` (`want = {"Positive":1,"Negative":2,"Exception":1}`) say the same. With no failure mode in the BRD, the only way to satisfy the rule is to invent wrong-type inputs.
3. **The revision loop keeps the type.** `design.py:61` says "Rewrite only this one test case, **keeping its type**", so a reviewer can never remove an invented Exception case. All 40 cases were sent back once and all 40 stayed REJECT (seq 175–197). The run spent 132,845 revision tokens with no case approved (seq 205).
4. **Nothing validates the input domain.** `TestCase.test_data` is a free `str` (`cases.py:18`). Nothing parses it into a value or compares its type with the requirement's or the data dictionary's input type (DR-001 = string). Nothing rejects prose such as "Input markdown: `- item`" or "A Python list containing …".
5. **The oracle label is self-declared.** `cases.py:21` accepts any of four labels. No code checks that a "specified" expected result appears in the requirement `quote`. CLAUDE.md requires model output to be checked against evidence; here only the confidence reviewer did that, and its REJECTs can be overridden.
6. **The `boundary` dataset defaults are applied regardless of type** (`qe/test_data.py:75-87`):
   - `_kinds` is a keyword regex over scenario, data, steps and expected result.
   - `type` containing "boundary", or any of the words `empty|maximum|minimum|overflow|zero|negative|too long|special character|unicode`, adds `boundary.number`. It also adds `boundary.string` only if `string|text|name|empty|special|unicode|long` appears (line 78).
   - TC-APP-002's scenario ends "(negative)", so it got `["boundary.number"]` for a Markdown string input.
   - Any `null` adds `boundary.json`, as TC-APP-004 shows.
   - `boundary_payload("string")` is a fixed generic payload (`test_data.py:26`): `"A"*1024`, an SQL-injection string, emoji. Nothing ties it to this domain.
   - **No generated test reads `datasets`.** 0 of 40 files contain the word, by grep of the worktree, so the shared datasets were dead weight.
7. **The case data is copied, not built.** `test_data.py:103` stores `mask(test_data)[:500]` under the key **`data`**. The generate prompt (`workflows/qe/generate/batch.py:25`) only says "each case's own data under "cases"" and never names the key. Three tests read `["test_data"]` and `["expected_result"]`, keys that do not exist. TC-APP-026, 029 and 032 failed with `KeyError: 'test_data'` (JUnit).
8. **The test design already had wrong cases, and the gate let them through.**
   - The design review gave 0 approved and 40 REJECT, with score 22 at Gate 3: TC-APP-003 "expected_derivable … it is a guess".
   - The Gate 3 summary text says "Remaining gaps: none" and does not mention the 40 REJECT. Approval needs only `feedback.strip()` to be non-empty (`maf/engine/__init__.py:80`), and the admin wrote `"a"` (ledger seq 118).
9. **Requirements were incomplete before design.** 15 requirements cover only FR-001 to FR-006; the reviewer said so (approval `cb1b278f` payload, score 75). There are no requirements for FR-007 to FR-011 (ordered lists, code blocks, blockquotes, horizontal rule, paragraphs), NFR-001 to NFR-004 or DR-001. So the one requirement that fixes the input type (DR-001) never reached design.
10. **Greenfield is not handled in design.** The confidence rubric (`source_proven`, `correct_target`) cannot pass without code, so every case is REJECT by construction. That makes the review useless for telling good cases from bad.
11. **The skill text is stale.** `skills/generating-test-data/SKILL.md:27` says the platform step is "planned: `qe/test_data.py`, not yet built". It is built, and it does not do "Schema Conformance" (line 17) because there is no schema.

### 3.6 What should check this in code

- **A domain validator in `qe/model`,** run from `design.py` before review:
  - For each case, parse `test_data` into a typed value.
  - Refuse a value whose type differs from the requirement's declared input type: DR rows, or a new `input_type` on the requirement from the requirements stage.
  - Refuse an `Exception` case whose expected error text is not in the requirement quote or BRD.
  - Refuse `oracle="specified"` unless the expected value or message appears in the requirement `quote`.
- **Make the Exception rule conditional** in `quota.py:coverage_gaps`, `apply_quota` and the `design.py:36` text: required only when the requirement or the code shows a failure path. Otherwise it is replaced by a second Negative, the way prompt line 1 already says.
- **`test_data._kinds`:** choose datasets from the declared input type, not from keywords. Drop `boundary.number` for string inputs, and never match the case's own type label ("negative").
- **Write the fixtures key contract into the generate prompt** (`batch.py:25`): name the keys `data` and `uses`. Add a static check that refuses a test reading a key that is not in fixtures.json.
- **Refuse QE design, generate and execute on a greenfield project,** or run them as an explicit "spec-first" mode with no confidence review on `source_proven`. The run should not spend 482 k tokens producing tests for code that does not exist.
- **Require a real reason** for accepting REJECT items: a minimum length, and a check that it is not the same as the gate title.

---

## 4. C: later stages

| Stage | What ran | Result and cause | Honest? |
|---|---|---|---|
| **generate** (07:41:46–07:43:20) | 58 calls; 40 files on branch `atlas/qe-388a90`, commit `bd0dd08` | Static checks: 40 failed; 34 still failed after one round (seq 239, 361). TC-APP-036 had invalid syntax (seq 360). Imports name **six invented modules**: `src.converter`, `md_converter`, `markdown_html_converter`, `src.skills.markdown_to_html`, `src.md_converter`, `converter` (grep of the worktree). **6 files define the converter locally**: TC-APP-008, 020, 026, 029, 032, 037. TC-APP-008 says "Simplified converter for testing" (`test_heading_TC_APP_008.py:9-17`). The review found this ("mocks/overrides the real implementation", G4 payload), but the static checks do not refuse it (`generate/files.py:32-48` has no "test defines the subject under test" rule). The fix message at `qe/emit/python.py:151` ("Use only the standard library, pytest, and what the repository's code already imports") points the model toward writing stubs when the repository has no code. | The G4 summary "40 of 40 cases have tests" is true but misleading: 34 carry unresolved findings (`emit_unresolved`). |
| **prepare** | env facts | "httpx 0.28.1, pytest-asyncio yes" (seq 413) | yes |
| **execute** (07:43:39) | pytest in the worktree | 40 tests: 31 collection errors (ModuleNotFoundError), 3 `ModuleNotFoundError` failures, 3 `KeyError: 'test_data'` failures, **3 passes: TC-APP-008, TC-APP-020, TC-APP-037, all testing local stubs.** The agent summary was refused for wrong counts (seq 421), and code's summary was used. | The counts are true. But the 3 "passes" exercise no application code. |
| **heal** | **not run** | `execute.py:42-44` routes greenfield straight to trace. The 3 KeyError failures are FIXTURE_DRIFT (`qe/execution/failures.py:84`), which healing is allowed to repair, but they stayed. | Skipping heal on greenfield is defensible. |
| **trace** (07:43:43) | matrix and summary | Verdict **FAIL**, 3/40, coverage 20 %. REQ-002, REQ-007 and REQ-015 are "covered" only by the stub tests (`doc_5aee5825af6f` data). Failure classes: 34 environment, 3 test problem, 0 defect. | **No.** No test touched application code, because none exists. CLAUDE.md treats zero real executions as INCONCLUSIVE. `trace.py:30` switches to INCONCLUSIVE only when `passed == 0` and every failure is ENVIRONMENT. The 3 stub passes and 3 KeyErrors defeat that rule, so it reports FAIL with 20 % coverage. The honest verdict is **INCONCLUSIVE: no code under test (greenfield), 0 tests exercised the product.** |
| **sign** (07:43:46) | confidence-reviewer release review: 13, REJECTED | `doc_156e8df87de0`; G5 approved by admin on FAIL, reason "done" | The review text is honest. Approving on FAIL is a human decision the system allows. |

---

## 5. D: logs, present and missing

### 5.1 What exists for this project

- **`app-2026-11-11.jsonl`:**
  - 1,678 `aqe.request` lines. Fields: request_id, method, path, status, duration_ms, and `user_id`, which is **always `"***"`** (2,063 such lines in the file by the end, 0 lines with `admin`).
  - 85 MAF warnings: "Dropping client-supplied 'assistant'/'tool' message …". These come from each harness resume after 06:37:50.
  - 2 `aqe.api` errors.
  - **No line carries a run_id, stage, agent, trace_id or thread_id.** No line exists for any QE stage, model call or gate. After 06:39:41 the app log holds only GET and POST request lines.
- **`errors-2026-11-11.jsonl`:**
  - 85 of 87 lines are the MAF "Dropping client-supplied …" warnings, which are noise.
  - `err_3b3363243860`: 412, no model configured.
  - `err_e2476efb2970`: 502, skill-creator, reply file `rep_145fb3c3fd45.txt`.
- **`run_events`.** 478 rows in all for the database: 42 for the BA run and 436 for the QE run. They hold stage_start and stage_end with timestamps, agent_call and agent (with tokens and prompt_ref), skill, review, warning, artifact and approved events. The `message` is redacted (`run_context.py:60`); the `data` JSON is **not**.
- **`spans`.** For this project: 917 GET and 14 POST server spans, 25 stage spans, 24 tool spans, and 9 workflow spans. Stage timing is present.
- **`agent_calls`, `tool_calls`, `ledger`** are as in §2.

### 5.2 Gaps

| Id | Gap | Example from this run |
|---|---|---|
| G1 | **Model input and output are not stored** for successful calls. `agent_calls` has tokens and latency only; `run_failures.reply_file` exists only on failure. | The prompt that produced TC-APP-008's "TypeError 'Input must be a string'" cannot be read back; §3.2 had to reconstruct it from code. |
| G2 | `agent_calls` has **no stage, trace_id, span_id, thread_id or request_id.** | The 44 test-design-architect calls (ids in the 07:39:26–07:40:41 range) cannot be split into first design, revision and redesign. The 22 harness calls cannot be tied to the 7 `/agui/harness` requests except by timestamp. |
| G3 | **App and error log lines have no run_id or trace_id,** although `core/logs.py:24` lists `run_id`, `stage` and `agent` as fields. No workflow code passes them. | `req_5cfd8f1ed649` started run_f1d60f388a90, but nothing in the log says so. |
| G4 | **The chat trace and the workflow trace are not linked.** | The `start_workflow` span is in trace `157eb647…`; the workflow root is trace `de1ac228…` at the same second, with no parent link. |
| G5 | **One trace per gate resume, with no common root.** | The QE run is spread over six traces: `de1ac228`, `5571608a`, `682cf005`, `6206a6ec`, `45b186ed`, `fdf1d91b`. |
| G6 | **The MAF tool-approval lifecycle is not logged.** There is no record of the interrupt id, tool, arguments, who answered, the answer or the time, in the ledger, the logs, `tool_calls` or the history file (0 `function_approval_*` contents). | `create_skill` at 06:37:05 → answered before 06:37:11. Only the post-execution `tool_calls` row 13 exists. |
| G7 | **Actor identity is masked everywhere.** | `user_id: "***"` on every request log line; `spans.attributes.user_id = "***"` on workflow spans; run_events "Approved by ***"; ledger seq 4 `reason: "***"`. |
| G8 | **Workflow spans carry a single `agent` attribute** for a whole multi-agent segment, and HTTP spans take the agent of a nested call. | Trace `682cf005` says agent=test-design-architect, though the confidence-reviewer ran too. The `/agui` span at 06:37:11 (`e96251e1`) says agent=**skill-creator**, not harness. |
| G9 | **No model-call spans.** | There are 129 QE model calls but no `chat`/`model` span per call. Only aggregate tokens sit on workflow and HTTP spans (15 spans with `tokens_in`). |
| G10 | **No heartbeat or progress during long model calls.** | requirements-analyst took 189,522 ms; run_events has no entry between seq 20 (06:39:51) and seq 24 (06:43:01). |
| G11 | **`run_failures` is empty for a run with 37 failed tests and 34 unresolved static findings.** | Failures live only in documents and run_event `data`. |
| G12 | **Gate waits are not surfaced.** No log line or notification marks how long a run waits for approval. | G1 waited 55 min 27 s (06:43:05 → 07:38:32). |
| G13 | **`run_events.data` is not redacted,** while `message` is. | seq 7: message `Approved by ***`, data `{"feedback":"admin"}`. The same text is masked in one field and not the other. |
| G14 | **MAF "Dropping client-supplied message" warnings flood `errors-*.jsonl`.** | 85 of 87 lines, and a real error would be lost among them. |
| G15 | **No record of why G0 was decided manually twice** during the QE run. | ledger seq 111 and 116 (07:40:55 and 07:40:58), run_id null. |

---

## 6. E: the approval report (item 3)

### 6.1 Did the model call a risky tool?

Yes, three times. `RISKY = {"start_workflow","run_tests","save_document","remember","create_skill"}` (`harness_kit/catalog.py:27`), and `harness.py:93-94` sets `approval_mode="always_require"` on them.

| Call | Model turn (asked) | Executed in | Gap |
|---|---|---|---|
| `create_skill` (request from BRD/Gherkin) | agent_call 57, 06:37:05, trace `e9ce1660` | tool_calls 13, 06:37:11–06:37:18, trace `e96251e1`, `req_f3b406705cb0` | 6 s |
| `create_skill` (document_id `doc_1c0c877362d0`) | agent_call 67, 06:38:38, trace `1f58d7b3` | tool_calls 20, 06:38:43–06:38:50, trace `6103c759`, `req_8eaf3b16ea6b` | 5 s |
| `start_workflow` (qe, "Markdown to HTML Converter - Full QE") | agent_call 74, 06:39:38, trace `a7748a89` | tool_calls 24, 06:39:41, trace `157eb647`, `req_5cfd8f1ed649` | 3 s |

### 6.2 Did MAF emit an approval request?

Yes. The evidence:

1. Each risky call ran in a **different request and trace** from the one that asked for it. That is MAF's interrupt-and-resume shape: "a risky tool ends the run with an approval interrupt, and the client's next request carries `resume`" (`agui.py:123-130`).
2. In the MAF snapshot, the assistant's text (index 25) comes **before** the tool result (index 26).
3. MAF runs a pending approved call only for a canonical `resume` entry with a boolean `approved` (`agent_framework_ag_ui/_agent_run.py:1203-1232`). No "Translated a legacy AG-UI tool-message approval" warning appears in the logs, so the canonical path was used.
4. The tools ran with `status=ok`, so the answer was `approved: true`.

### 6.3 Why the user says no card appeared

- **The only client code that sends `resume`** is the Approve/Reject card. `RunStatus.tsx:49` stores `params.interrupts` when `outcome === "interrupt"`, `RunStatus.tsx:68-83` renders the card, and `Conversation.tsx:74-80` sends `runOnce(resume)` on click. The frontend matches `@ag-ui/client` 1.0.2 (`onRunFinishedEvent` gives `outcome:"interrupt"` and `interrupts`), and MAF builds the interrupt as `{id, message:"Approve running create_skill?", metadata.agent_framework.function_call}` (`_run_common.py:480-505`).
- **So the data says a card was answered three times,** 3 to 24 s after each interrupt. **Which person clicked it is not recorded (G6).** I did not reproduce this in a browser, so whether the card was easy to see is **not verified**.
- **Why it then looks as if no approval was asked:**
  1. **The card leaves no trace.** It is removed on answer (`Conversation.tsx:79`). It is never written to `chat_messages`, the ledger or the history file. Reopening the thread shows no approval at all.
  2. **The transcript duplicates the user's message** instead of showing an approval. `agui.py:84-89` appends `last_user` on every request, including a `resume` request that carries no new user text. Chat seq 1/3, 7/9 and 11/13 share ids `3ffc69d4…`, `1e13a0ae…` and `6461bf02…`.
  3. **MAF's snapshot replays old user turns on resume.** Snapshot indexes 49–50, 53–54 and 69–71 re-insert "approve", "i ahve already approved it" and "apporved fomr studio" between the tool call and its result. The model then answers "Great, the plan was approved from Skill Studio!" (chat seq 12). That is false: both harness plans `spl_0ebcbd9403f1` and `spl_acf593aaa8ca` are still `draft`, and no approve request exists for them.
  4. **The approval the owner did see was a different system.** `start_workflow` started run_f1d60f388a90. Its gates are **workflow gate approvals** in the `approvals` table, shown on the project Approvals and Governance pages. Gate 1 `cb1b278f-bf5d-40f5-91e9-1f890c138fd0` appeared at 06:43:05, 3 min 24 s after the chat turn ended, and waited 55 min. The chat never shows gate approvals: no tool, event or notification relays them. The harness only said "Gates will need named human approval on the Governance page" (chat seq 14).
  5. Gate 0 did not appear for the QE run, because it was already approved from the BA run (`shared/intake.py:19-20`). So the first approval the owner saw was in the project, not the chat.

### 6.4 The two approval kinds

| | MAF tool approval (chat) | Workflow gate approval (project) |
|---|---|---|
| Raised by | MAF `ToolApprovalMiddleware` for `approval_mode="always_require"` (`harness.py:93-94`) | `StageSpec.approval`, for example `_doc_gate` (`qe/common.py:59-75`), via `engine` |
| Stored | in memory only (`harness_kit/snapshots.py:21` `InMemoryAGUIApprovalStateStore`); lost on restart | `approvals` table, `gates` table, ledger `gate.*` |
| Shown | `ApprovalCards` in the chat, only until answered | Approvals page, `GatePipeline.tsx`, `RunPanel.tsx` |
| Audit | none (G6) | `decided_by`, `decided_at`, signature, ledger |

### 6.5 Precise root cause

There are three faults:

- `agui.py:89` writes a duplicate user row on every resume, and the transcript shows no approval.
- Nothing persists or logs the tool-approval decision (`harness_kit/snapshots.py:21`, `Conversation.tsx:74-80`).
- No path brings workflow gate approvals, or a link to them, into the chat that started the run (`maf/tools` `start_workflow` returns only `{run_id, status, view}`, tool_calls 24).

The model's false "approved" acknowledgement comes from the replayed user turns in the MAF snapshot (indexes 49–50, 53–54, 69–71). The likely trigger is the client re-sending the full transcript on resume (85 "Dropping client-supplied" warnings), and MAF merging that transcript wrongly. That trigger is **not verified** in the MAF code.

---

## 7. F: the `***` report (item 4)

**Where the approver is stored:**

| Store | Value |
|---|---|
| `approvals.decided_by` | `'admin'` for all 7 rows, e.g. `cf0bb2f4-…`, `cb1b278f-…` |
| `gates.decided_by` | `'admin'` for G0 to G5 |
| `ledger.actor` | `'admin'` for all `gate.approved` rows |
| `run_events.message` (immutable) | `Approved by ***`, e.g. run_d5d37df5f1d2 seq 7 and 41; run_f1d60f388a90 seq 31, 43, 213, 411, 435 |
| ledger seq 4 `data.reason` | `"***"`, although `approvals.feedback = 'admin'` for the same decision |
| request log `user_id` | `"***"` on every line |
| `spans.attributes.user_id` | `"***"` |
| harness `project_status` result (snapshot index 37) | `"decided_by": "***"` |

**Why it renders `***`:**

1. **A registered secret equal to the text `admin` existed at run time.** At `HEAD 5a5e6df`, `core/security.py:119-122` read `if len(value) >= 4: _known_secrets.add(value)`, and `redact()` (`security.py:136-139`) replaced every occurrence of a known secret with `***`. The admin password is registered at `core/auth/base.py:38` (`register_secret(password)`); MCP secrets are registered at `core/mcp/registry.py:65,92`. Ledger seq 4 shows the input `admin` (raw in `approvals.feedback`) became exactly `***`, with no letters left over. So a registered secret equalled `admin`, which is consistent with the admin password being the same as the username. I did not read the `.env` secrets. The uncommitted working-tree change at `security.py:119` (`MIN_MASKED = 12`) names exactly this case ("a password like 'admin' turned every 'admin' into ***") and adds `weak_secret()`. The server process still ran the old code: log lines up to 07:57:34 still show `user_id: "***"`, and `security.py` was changed at 07:46:17 UTC.
2. **The approver's name is stored in redacted free text.** `maf/engine/stages.py:76` logs `f"Approved by {answer['by']}"`. `maf/engine/run_context.py:60` stores `redact(message)`, so the row holds `Approved by ***`.
3. **The run view parses the name back out of that text.** `api/runs.py:66` sets `decided_by = message.removeprefix("Approved by ")`, which gives `"***"`. `auth.named()` (`core/auth/users.py:69-72`) finds no account `***` and falls back to the raw value. `features/runs/RunPanel.tsx:131` then renders "Approved by ***".
4. **The approvals and gate pages read `approvals.decided_by` or `gates.decided_by`** (`'admin'`) through `named()` / `display_names()` (`users.py:18-29`, "Administrator"). Those pages are not affected. The run timeline and the harness chat are.

The fix in the working tree stops new masking after a restart. **It does not repair the stored rows**: `run_events` are immutable and still say `Approved by ***`. `api/runs.py:66` should read the approver from `approvals.decided_by` for the run, joined by gate, instead of from the message.

---

## 8. Bugs found

| Id | Sev | File:line | Evidence | Proposed fix | Test that would catch it |
|---|---|---|---|---|---|
| B1 | High | `qe/model/quota.py:19-20`, `:107`; `workflows/qe/design.py:36,61` | 10 Exception cases with invented TypeError and ValueError; run_event seq 198 | Require an Exception case only when the requirement or code states a failure path; otherwise a second Negative. Let revision change the type. | Unit: `coverage_gaps` with a requirement that has no failure path → no "no Exception case" gap |
| B2 | High | `prompts/test-design-architect.md:1` vs `:3`; `skills/designing-test-cases/SKILL.md:20-21` | Contradictory Exception rule; numeric-only boundaries | One rule: "Exception only when failure handling exists; boundaries of the requirement's input type" | Eval case in `evals/` with a string-only requirement: no non-string input in the output |
| B3 | High | `qe/model/cases.py:18,21` (no domain or oracle check) | `test_data:"None"`, `"42"`; `oracle:"specified"` for text not in the BRD | Validator: parse `test_data`; check its type against the requirement's input type; a "specified" result must appear in `quote` | Unit: a case with `test_data="42"` for a string-input requirement → refused |
| B4 | Med | `qe/test_data.py:77-78` | TC-APP-002 tagged `boundary.number` because of the word "(negative)" | Pick datasets from the declared input type, never from keywords | Unit: a `Negative` case on a string input → `uses` has no `boundary.number` |
| B5 | Med | `qe/test_data.py:103` + `workflows/qe/generate/batch.py:25` | `KeyError: 'test_data'` in TC-APP-026, 029, 032 | Name the keys (`data`, `uses`) in the prompt; a static check refuses unknown fixture keys | Unit for `_generated_file_problems`: a file reading `["test_data"]` → finding |
| B6 | High | `workflows/qe/generate/files.py:32-48`; `qe/emit/python.py:151` | 6 tests define the converter locally; 3 "pass" | Refuse a test that defines a function with the name it is meant to import; change the message to "import the repository's real module" | Unit: content with `def convert_markdown_to_html` and no import of it → finding |
| B7 | High | `workflows/qe/trace.py:30` | FAIL, 20 % coverage, from stub-only passes on an empty repo | INCONCLUSIVE when `mode == greenfield`, or when no test imports repository code | Unit: greenfield results with 3 passes → INCONCLUSIVE |
| B8 | High | `core/security.py@HEAD:121` (fixed uncommitted at `:119-126`) | `***` for `admin` everywhere | Commit the MIN_MASKED fix and restart; refuse a password equal to the username at startup | Unit: `register_secret("admin")`; `redact("Approved by admin") == "Approved by admin"` |
| B9 | Med | `api/runs.py:66`; `maf/engine/stages.py:76`; `run_context.py:60` | `decided_by` parsed from redacted text | Store `{"by": id}` in event `data` and read it from there or from `approvals` | API test: run events after an approval → `decided_by_name == "Administrator"` |
| B10 | Med | `maf/agui.py:84-89` | Duplicate user rows chat seq 3, 9, 13 | Skip `_append` when `body.resume` is set, or when the message id already exists in the thread | Unit: two POSTs with the same last user id, the second with `resume` → 1 row |
| B11 | Med | `harness_kit/snapshots.py:21`; `features/chat/Conversation.tsx:74-80` | No record of 3 approvals (G6) | Ledger `harness.tool_approval` (tool, args hash, interrupt id, decision, who); show the answered card in the transcript | E2E `tests/e2e/test_harness_stories.py`: after Approve, the ledger and chat contain the decision |
| B12 | Med | `maf/tools` `start_workflow` result (tool_calls 24) | Gate 1 only on the project page; the chat is silent for 55 min | Return pending gate links; post a chat notice when the run waits on a gate | E2E: start_workflow from chat → the chat shows "waiting for Gate 1" with a link |
| B13 | Med | MAF snapshot merge on resume (`agui.py:126-130`, client full replay) | Old user turns re-inserted (snapshot idx 49–50, 53–54, 69–71); false "approved" claim | Send only the resume on a resume (no message replay), or dedupe by id | Integration: a resume after an interrupt → the snapshot has no repeated user turn |
| B14 | Low | `maf/engine/__init__.py:80` | REJECT accepted with reason `"a"` (ledger seq 118) | Minimum reason length and wording check | Unit: `decide(..., feedback="a")` with REJECT items → ValueError |
| B15 | Low | `core/gates.py:76` | `test_data`, `test_code` and `release` stay draft after G3 to G5 | Map test_data → G3, test_code → G4, release/traceability/defect_report → G5 | Unit: `decide(gate=3)` → test_data doc approved |
| B16 | Low | `skills/generating-test-data/SKILL.md:27` | Says "not yet built" | Update the text | Docs lint |
| B17 | Med | QE workflow has no greenfield guard (`workflows/qe/definition.py:29-42`) | 482 k tokens on a 0-file repository | Stop at G0 with "no code to test", or offer a spec-first mode | Integration: QE run on an empty repo → stops with a clear message |
| B18 | Low | `maf/engine/run_context.py:60` | `message` is redacted, `data` is not (seq 7) | Redact both, or neither, with the same rule | Unit: `add_event` with a secret in `data` → masked |

### Fixed (Phase Q1, 2026-11-11, offline with `ScriptedClient`; not yet rerun on the real model)

| Bug | Fixed | Where | Test |
|---|---|---|---|
| B1 | Yes. Exception required, and kept first by the quota, only when the requirement states error behaviour (`error_behaviour`, or a raise or throw on the quote); otherwise a third Negative. The revision may turn an invented Exception case into a Negative one | `qe/model/quota.py`, `qe/model/domain.py`, `workflows/qe/design.py` | `tests/test_core_runs.py::test_coverage_gaps_and_duplicates`, `tests/test_budget_quota.py::test_a_cut_keeps_the_plugins_required_kinds_first` |
| B2 | Yes. One Exception rule, typed boundaries in `prompts/test-design-architect.md` (seeded as a new prompt version) and `skills/designing-test-cases/SKILL.md`; the requirements prompt asks for `input_type` and `error_behaviour` | prompts, skill | eval `string_input_has_no_invented_errors` in `evals/test-design-architect.json` (needs the real model) |
| B3 | Yes. Test data of another type than the requirement's `input_type` goes back once, then is refused and named in the Gate 3 gaps. The oracle is a required field | `qe/model/domain.py`, `qe/model/schemas.py` | `tests/test_qe_correctness.py::test_test_data_of_another_type_than_the_string_input_is_refused`, `::test_a_case_of_the_wrong_type_is_revised_then_refused_at_gate_3`, `::test_every_case_needs_an_oracle_and_input_types_are_named_one_way` |
| B4 | Yes. Boundary datasets from the input type only | `qe/test_data.py` | `tests/test_stages_classification.py::test_datasets_follow_the_input_type_never_the_wording` |
| B5 | Yes. The prompt names `data` and `uses`; a test reading a case field from fixtures.json is refused | `workflows/qe/generate/batch.py`, `files.py` | `tests/test_qe_correctness.py::test_reading_a_key_fixtures_json_does_not_have_is_refused` |
| B6 | Yes. A Python test that defines, shadows or monkeypatches its subject, or defines code and imports none from the repository, is refused | `qe/emit/subject.py`, `generate/files.py` | `tests/test_qe_correctness.py::test_a_test_that_defines_or_stubs_its_subject_is_refused` |
| B7 | Yes. INCONCLUSIVE when the mode is greenfield or no executed test reached the repository's code | `qe/trace.py`, `workflows/qe/trace.py` | `tests/test_qe_correctness.py::test_stub_only_or_greenfield_results_are_inconclusive` |
| B14 | Yes. Approving REJECT items or rejecting a gate needs 10+ characters, two words, not the gate title | `maf/engine/__init__.py` | `tests/test_qe_correctness.py::test_approving_reject_items_with_a_one_letter_reason_is_refused`, `::test_a_reason_for_a_reject_decision_must_be_real` |
| B15 | Yes. G3 approves test_cases, gherkin, test_data; G4 test_code; G5 release, traceability, defect_report | `core/gates.py` | `tests/test_qe_correctness.py::test_gates_3_to_5_approve_the_documents_they_cover` |
| B16 | Yes | `skills/generating-test-data/SKILL.md` | `tests/test_skills_loading.py` (loads it) |
| B17 | Yes. Stops before Gate 0 with "No code to test" and no model call; `{"spec_first": true}` keeps the greenfield path | `workflows/qe/definition.py` | `tests/test_qe_correctness.py::test_qe_on_a_repository_with_no_code_stops_before_gate_0_without_a_model_call` |
| B18 | Yes | `maf/engine/run_context.py` | `tests/test_qe_correctness.py::test_run_event_data_is_redacted_like_the_message` |

B8 to B13 belong to Q2 and Q3 and are not fixed here. Known limits: the error-behaviour signal is the analyst's field or a raise or throw on the quote line, and the analyst's field is not checked against the document; the subject check reads Python only; a "specified" oracle is not yet checked against the quote.

---

## 9. Gaps in logs

These are the same as §5.2, ordered by debugging value:

1. **G1.** Model input and output are not stored for successful calls. They cannot be linked to a run, stage or document.
2. **G6.** The harness tool-approval lifecycle (request, decision, actor, time) is not logged anywhere.
3. **G2, G3.** No stage, trace or thread on `agent_calls`; no run_id or trace_id on any app or error log line.
4. **G4, G5.** The chat trace is not linked to the workflow trace it starts, and each gate resume opens a new, unlinked trace.
5. **G7.** Actors are masked (`user_id: "***"`, "Approved by ***", spans `user_id: "***"`).
6. **G8, G9.** No per-model-call span, and the `agent` attribute on workflow and HTTP spans is wrong for multi-agent segments.
7. **G10, G12.** No progress during a 189 s model call; no record of gate wait time (55 min on G1).
8. **G11.** `run_failures` is empty for a run with 37 failed tests.
9. **G13.** `run_events.data` is not redacted while `message` is.
10. **G14.** 85 MAF "Dropping client-supplied message" warnings drown the errors log.
11. **G15.** No reason or context is recorded for the manual G0 decisions at 07:40:55 and 07:40:58.

**Not verified:**

- The approval card was not reproduced in a browser.
- The MAF snapshot-merge cause of B13 was not traced through the code.
- Why G0 was re-decided during the QE run: not found in the data.
