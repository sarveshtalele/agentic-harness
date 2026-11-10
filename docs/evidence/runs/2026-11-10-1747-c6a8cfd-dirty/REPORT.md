# Evidence report c6a8cfd-dirty

Generated 2026-11-10T12:17:44+00:00 · model deepseek-v4-flash-global · overall **FAIL**

| Level | Verdict | Executed | Passed | Failed | Errors | Skipped | Seconds | Source |
|---|---|---|---|---|---|---|---|---|
| unit-integration | PASS | 606 | 606 | 0 | 0 | 0 | 121.1 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/unit-integration.xml` |
| smoke | PASS | 3 | 3 | 0 | 0 | 0 | 8.8 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/smoke.xml` |
| live-harness | PASS | 1 | 1 | 0 | 0 | 0 | 8.0 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/live-harness.xml` |
| e2e-real-model | FAIL | 33 | 30 | 3 | 0 | 0 | 1818.3 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/e2e-run5.xml` |

## Failing cases

- **e2e-real-model** `tests.e2e.test_app::test_11_qe_lifecycle_real_model_real_pytest`: AssertionError: Timed out waiting for Gate 3
- **e2e-real-model** `tests.e2e.test_finance_repo::test_f4_feature_builder_adds_the_tool`: AssertionError: Approval needed
  Review change: Add savings goal tool
  
  Test verdict FAIL. Fix: update tests to import calculate_savings_goal_tool from the register function and fix the total tool count in integration test
  
  Independent confidence review
  60 of 100
  REVISE
  Tests fail with
- **e2e-real-model** `tests.e2e.test_finance_repo::test_f8_record_token_use`: AssertionError: [{'workflow': 'qe', 'status': 'completed', 'tokens_in': 576625, 'tokens_out': 122737, ...}, {'workflow': 'change', 'status': 'completed', 'tokens_in': 41851, 'tokens_out': 6494, ...}, {'workflow': 'change', 'status': 'completed', 'tokens_in': 13195, 'tokens_out': 431, ...}, {'workflo

## Screenshots

- `docs/evidence/runs/2026-11-10-azure-package-tour/account.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/agents.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/approvals.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/docs.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/documents.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/findings.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/harness.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/harness_chat.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/home.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/mcp.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/observability.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_approvals.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_ba.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_bugs.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_documents.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_feature.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_governance.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_observability.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_prompts.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_qe.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_repository.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/projects_project_runs.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/settings.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/skills.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/skills_studio.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/templates.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/usage.png`
- `docs/evidence/runs/2026-11-10-azure-package-tour/users.png`

## Not verified

- Every listed level executed tests.
