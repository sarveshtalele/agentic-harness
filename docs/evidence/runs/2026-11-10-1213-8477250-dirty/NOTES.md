# P1 evidence notes (2026-11-10)

| Check | How it ran | Result |
|---|---|---|
| Unit + integration | `pytest -m "not e2e and not live and not smoke" --junitxml` | 588 passed, 0 failed (see REPORT.md) |
| CI gate 1, no new fabricated values | `tests/test_no_fabrication.py` | pass; ratchet baseline 76 known cases in 18 files |
| CI gate 4, agents approve nothing | `tests/test_agents_approve_nothing.py` (static with alias resolution + every harness tool run against a real project) | pass |
| Frontend types / lint | `tsc --noEmit`, `eslint` | 0 errors / 0 problems |
| Live page tour | Backend and UI started through the Browser pane (`.claude/launch.json`, throwaway data dir and generated test admin), Playwright 1.64.1 Chromium signs in and opens 28 pages | 28 of 28 HTTP 200, 0 console errors, 0 failed requests, 0 error screens. Screenshots and `page_tour.json` in `../2026-11-10-p1-page-tour/` |
| Live page tour, wording | Same run, text search | `/harness` still shows "Specter" and "Cloudflare", `/skills` "Specter" and "A+" (plan D-24, D-25, phase P3c) |
| Backend log | Browser pane server log after restart | No errors; the uvicorn access-log crash from `install_log_mask` is fixed (`tests/test_log_mask.py`) |
| Smoke (`tests/e2e/test_smoke.py`) | `pytest -m smoke` | 3 setup errors: `next build` (Turbopack) cannot bind a local port in this environment ("Operation not permitted"), inside and outside the command sandbox. Not a code failure. Allow local binding (`sandbox.network.allowLocalBinding: true`) or run in CI |

## Not verified

- Smoke and E2E levels did not execute here (build blocked as above). The live page tour covered page loading but not the smoke test's sign-in refusal and non-admin checks.
- No live model run: harness chat, BA and QE workflows with the real model were not exercised in P1.
- Windows and Linux: not run locally; CI covers them once pushed.
