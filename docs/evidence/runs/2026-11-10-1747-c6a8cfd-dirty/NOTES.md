# Full test pass notes (2026-11-10)

## Results by level

| Level | How it ran | Result |
|---|---|---|
| Unit and integration | `pytest -m "not e2e and not live and not smoke"` | 606 passed, 0 failed |
| Smoke | `tests/e2e/test_smoke.py` through a Browser-pane launch config; the command sandbox blocks the Turbopack build from opening a port | 3 of 3 |
| Live harness | `tests/test_maf_harness_live.py` on deepseek-v4-flash-global | pass: `load_skill` and `todos_add` called, 3 model calls recorded |
| E2E, real model and real browser | `tests/e2e`, 33 tests, five runs during the fixes | Run 1: 2. Run 2: 18. Run 3: 20. Run 4: 32 (only `test_13` failed: the model wrote its tool call as text). Run 5, final code: 30 (JUnit in this folder) |
| Azure package | Both Kudu zips unpacked; the real `startup.py` (fresh venv from the package `requirements.txt`) and `startup.js` (`npm ci`, standalone build) on ports 8020 and 3020 | Health 200, 19 skills, DELETE journal, 28 of 28 pages HTTP 200 with 0 console errors, harness chat reaches MAF. Screenshots in `../2026-11-10-azure-package-tour/` |

## Run 5 failures, each traced

- `test_11`: the model endpoint dropped during test design ("Splitting a design batch of 4 requirements: Cannot reach the model endpoint."). The app split the batch, retried, and reached Gate 3 after the test's 420 s wait ran out; the run waits at Gate 3. It passed in run 4.
- `test_f4`: Feature Builder's change failed the repository's own tests. The code computed verdict FAIL and capped the review at 60, which is correct behaviour for a bad change. It passed in run 4. `plan.md` already records this as a known Feature Builder weakness.
- `test_f8`: the QE run used 699,362 tokens against the test's 600,000 budget; the earlier recorded run used 446,876. The test stays strict.

## Defects found by running and fixed

- Creating a project closed the dialog instead of opening the project (`364e868`)
- The in-project Chat tab redirected to the legacy harness (`0a80268`)
- The QE runner came from the model's free-text label; "python" ran nothing (`qe/execution.pick_runner`)
- Chat showed and stored the model's tool-call markup; it now ends with `AQE-MODEL-TOOL-TEXT`
- `ConfirmModal` had no dialog role
- Azure package:
  - prompts and skills were not found inside the package
  - WAL was set on the `/home` share
  - no allowed hosts, allowed origins, or admin were set
  - untracked files were packaged
  - `startup.js` left dangling symlinks, so `/api/copilotkit` crashed

## Not verified

- A real Azure deployment (needs the owner's subscription)
- The real model through the packaged UI (the packaged database has no model, and the agent does not type a real key into Settings)
- Windows and Linux (CI after push)
