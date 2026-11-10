# Harness page on MAF and P3 plugin discovery (2026-11-10)

| Level | Result |
|---|---|
| Unit and integration | 618 passed, 0 failed |
| Smoke (production build, real browser) | 3 of 3 |
| E2E, real model (deepseek-v4-flash-global) and real browser | 34 of 34, including the new `test_13b_harness_page_plans_scans_and_shows_todos` |

`13b-harness-page.png`: on `/harness` the MAF harness called `todos_add`, then `scan_repository`, then `todos_complete`. It reported the real finding S602 (`subprocess` with `shell=True`, `admin.py:5`), and the todo panel shows the item struck through. Both the panel and the scan result come from stored state and the real analyzer.

## Changes

- `/harness` renders the MAF Chat preset to the harness agent, with the thread's MAF todos (`GET /api/chats/{thread}/todos`, read through MAF's `TodoFileStore`). The legacy engine is at `/harness?engine=legacy`.
- New harness tools:
  - `run_tests` runs the registered runner via `qe/execution.run_suite` in the sandbox clone, with counts from JUnit.
  - `scan_repository` runs `static_analysis.run_all` and saves nothing.
  - `sandbox_status` reports measured fields only.
  - All three refuse when there is no repository. There is no general shell tool.
- P3 discovery: `core/plugins.py`, `GET /api/plugins`. Harness skills come from the discovered plugins, minus command skills (agentic-qe `qe-*`).
- UI no longer claims "MAF 2.0". The installed `agent-framework` is 1.24.

## Not verified

- Live run of `run_tests` from the chat on the real model. The offline tests run real pytest in the sandbox through the tool, but no model-driven call was exercised.
- Windows and Linux (CI after push).
