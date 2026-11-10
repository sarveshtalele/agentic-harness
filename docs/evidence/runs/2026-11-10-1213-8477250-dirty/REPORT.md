# Evidence report 8477250-dirty

Generated 2026-11-10T06:43:09+00:00 · model none (offline levels) · overall **FAIL**

| Level | Verdict | Executed | Passed | Failed | Errors | Skipped | Seconds | Source |
|---|---|---|---|---|---|---|---|---|
| unit-integration | PASS | 588 | 588 | 0 | 0 | 0 | 119.3 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/unit-integration.xml` |
| smoke | FAIL | 3 | 0 | 0 | 3 | 0 | 0.8 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/smoke.xml` |

## Failing cases

- **smoke** `tests.e2e.test_smoke::test_a_wrong_password_is_refused_and_the_right_one_signs_in`: failed on setup with "subprocess.CalledProcessError: Command '['/usr/local/bin/npm', 'run', 'build']' returned non-zero exit status 1."
- **smoke** `tests.e2e.test_smoke::test_main_pages_open_and_show_their_empty_state`: failed on setup with "subprocess.CalledProcessError: Command '['/usr/local/bin/npm', 'run', 'build']' returned non-zero exit status 1."
- **smoke** `tests.e2e.test_smoke::test_a_non_admin_is_refused_on_users`: failed on setup with "subprocess.CalledProcessError: Command '['/usr/local/bin/npm', 'run', 'build']' returned non-zero exit status 1."

## Screenshots

- `docs/evidence/runs/2026-11-10-p1-page-tour/account.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/agents.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/approvals.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/docs.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/documents.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/findings.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/harness.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/home.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/mcp.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/observability.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_approvals.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_ba.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_bugs.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_documents.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_feature.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_governance.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_observability.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_prompts.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_qe.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_repository.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/projects_project_runs.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/settings.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/skills.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/skills_studio.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/templates.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/usage.png`
- `docs/evidence/runs/2026-11-10-p1-page-tour/users.png`

## Not verified

- Every listed level executed tests.
