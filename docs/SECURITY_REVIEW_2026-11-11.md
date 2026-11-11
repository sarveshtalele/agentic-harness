# Security and dependency review, 2026-11-11

This review records the scans that were run, what they found, what was fixed, and what is accepted and why. Every line comes from a command run on 2026-11-11 on branch `feature/maf-harness-platform`. Run the same commands to repeat it.

## 1. Dependency audits

| Scope | Command | Before | After | What changed |
|---|---|---|---|---|
| Python, `requirements.txt` | `.venv/bin/python -m pip_audit -r requirements.txt` | 5 advisories, all in `chromadb` 1.5.9, with no fixed version | **0** | `chromadb` removed: no code imports it (the old RAG store was retired) |
| Python, `requirements-evals.txt` (optional RAGAS) | `.venv/bin/python -m pip_audit -r requirements-evals.txt` | 2 packages | 2 packages, accepted (section 3) | |
| UI, production packages | `cd src/frontend && npm audit --omit=dev` | 33: 21 high, 6 moderate, 6 low | **19: 18 high, 1 moderate**, from 2 root advisories, accepted (section 3) | npm `overrides`: `undici` ^6.29.1 (11 advisories, and with it `@fastify/busboy` 2), `katex` ^0.18.2, `graphql-scalars` ^2.0.1. The UI builds and passes `tsc` and lint with them |
| Desktop shell | `cd apps/desktop && npm audit --omit=dev` | 0 | 0 | |

## 2. Code scan (Bandit)

Command: `.venv/bin/python -m bandit -r src/backend scripts apps/desktop/backend_entry.py deploy/azure -ll -ii`. Before: 0 high, 36 medium. After: 0 high, 30 medium, all reviewed.

| Finding | Where | Decision |
|---|---|---|
| B314: XML parsed with the standard library | `qe/execution/runners.py` (JUnit reports from running the repository's own, untrusted, code) | **Fixed:** `defusedxml`. An unsafe or broken report counts as no results, so the run is INCONCLUSIVE, never PASS |
| B314: unsafe fallback parser | `repos/doc_parser/security.py` | **Fixed:** the fallback to `xml.etree` was removed. `defusedxml` is a requirement, so there is no unsafe path |
| B314 | `scripts/evidence_html.py`, `scripts/evidence_report.py` | **Fixed:** `defusedxml` (the reports can carry text from the code under test) |
| B108: `HOME=/tmp` for sandbox commands | `repos/sandbox/env.py` | **Fixed:** `tempfile.gettempdir()`, which is also correct on Windows |
| B608: SQL text built with an f-string (27) | `api/observability.py`, `core/tracing/queries.py`, `maf/observability.py`, `core/auth/users.py`, `core/gates.py`, and others | **Reviewed, no change.** Each puts only fixed clauses, `?` placeholder lists, or column names from a fixed list into the text; every value goes as a parameter |
| B310: `urlopen` | `scripts/dev.py`, `scripts/azure_local.py` | **Accepted:** health checks to `127.0.0.1` in developer scripts |
| B104: bind to all interfaces | `deploy/azure/backend_startup.py` | **Accepted:** App Service routes to the container on `0.0.0.0`; the API is closed to everything but the UI by the access restriction (guide section 10) |

## 3. Accepted risks

| Package | Advisory | Why it cannot be fixed now | Why it is acceptable | Revisit when |
|---|---|---|---|---|
| `zod` 3.25.76 (inside CopilotKit 1.83, `@ag-ui` 1.0.2); 18 high findings, one advisory | GHSA-mrhx-c7xc-m3w5: memory exhaustion on oversized constrained collections | CopilotKit pins the zod 3 API; zod 4 is not compatible | The CopilotKit route (`app/api/copilotkit/[[...path]]/route.ts`) first asks the backend for the caller's session, so a signed-out request never reaches zod. It now also refuses bodies over 2 MB with 413 | CopilotKit moves to zod 4 |
| `@hono/node-server` 1.19.17 (inside `@copilotkit/runtime`) | GHSA-rmxm-3fg6-px4f: `serveStatic` path double decoding | The fix is the 2.x major version, which the runtime does not accept | The app never uses Hono's `serveStatic`; Next.js serves static files | The runtime accepts 2.x |
| `langchain-text-splitters` 0.3.11 (RAGAS extra) | PYSEC-2026-77, fixed in 1.1.2 | `ragas==0.4.3` needs `langchain` below 1.0 | Optional: installed only with `ATLAS_INSTALL_EVALS=1`, and run by admins on evaluation data, never on user uploads | RAGAS supports langchain 1.x |
| `diskcache` 5.6.3 (RAGAS extra) | PYSEC-2026-2447, no fixed version | No release fixes it | Same as above: optional, admin-only | A fixed release |

## 4. Controls checked by the test suite (674 tests pass on PostgreSQL)

| Control (CLAUDE.md) | Test |
|---|---|
| Every API path is denied by default; each route has an ownership rule | `tests/test_access_routes.py` |
| Agents never approve a gate | `tests/test_agents_approve_nothing.py` |
| No fabricated data in production code | `tests/test_no_fabrication.py` |
| Passwords, usernames and secrets never reach a table or a log | `tests/test_api_access.py::test_passwords_and_usernames_never_reach_storage_or_logs`, `tests/test_models_usage.py::test_a_secret_and_a_password_in_a_reply_or_request_reach_no_table_or_log`, `tests/test_errors_records.py` |
| A secret in a tool argument never reaches a stored span | `tests/test_tracing_tools.py` |
| Harness shell: allowlist, approval per command, no shell, timeout, clean environment | `tests/test_harness_world.py` |
| Plugin hooks block dangerous commands (`rm -rf /`) | `tests/test_harness_plugin_hooks.py` |
| Key Vault: only `https://<name>.vault.azure.net`; a failure stops startup; values never logged | `tests/test_keyvault.py` |
| Templates are Markdown only | `tests/test_api_projects.py`, `tests/test_approvals_and_templates.py` |

## 5. Not covered by this review

- **No penetration test** of the deployed Azure app, because it has not been deployed yet.
- **Repository code still runs on the shared App Service host,** inside its folder and with a clean environment, but not in a container. Do not admit untrusted users until runs move to Container Apps Jobs (CLAUDE.md, Security).
- **The desktop installers are unsigned.**
- **The `npx` MCP check in the desktop profile was not run here:** auto mode refused to download and run a package from the npm registry. `docs/DESKTOP_RELEASE_GUIDE.md` section 8 has the steps to run it yourself.
