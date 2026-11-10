# Evidence report 8477250-dirty

Generated 2026-11-10T06:21:41+00:00 · model not recorded · overall **FAIL**

| Level | Verdict | Executed | Passed | Failed | Errors | Skipped | Seconds | Source |
|---|---|---|---|---|---|---|---|---|
| unit-integration | FAIL | 583 | 582 | 1 | 0 | 0 | 119.9 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/unit-integration.xml` |
| smoke | FAIL | 3 | 0 | 0 | 3 | 0 | 44.2 | `/Users/sarveshtalele/Downloads/agentic-harness/data/evidence/smoke.xml` |

## Failing cases

- **unit-integration** `tests.test_harness_project_scoped_features::test_harness_bug_fixes_query_grounded_in_centralized_db`: assert '| Bug ID | Severity | Location | Defect Description / Title | Rule | Status |' in 'data: {"type": "AGENT_SWITCH", "agentId": "qe-engine", "agentName": "Autonomous QE Engine"}\n\ndata: {"type": "THOUGH...datedAt": 1794291630299}}, "toolsUsed": {"scan_defects": 1}}}\n\ndata: {"type": "RUN_FINI
- **smoke** `tests.e2e.test_smoke::test_a_wrong_password_is_refused_and_the_right_one_signs_in`: failed on setup with "subprocess.CalledProcessError: Command '['/usr/local/bin/npm', 'run', 'build']' returned non-zero exit status 1."
- **smoke** `tests.e2e.test_smoke::test_main_pages_open_and_show_their_empty_state`: failed on setup with "subprocess.CalledProcessError: Command '['/usr/local/bin/npm', 'run', 'build']' returned non-zero exit status 1."
- **smoke** `tests.e2e.test_smoke::test_a_non_admin_is_refused_on_users`: failed on setup with "subprocess.CalledProcessError: Command '['/usr/local/bin/npm', 'run', 'build']' returned non-zero exit status 1."

## Screenshots

- `docs/evidence/screens/agents.png`
- `docs/evidence/screens/documents.png`
- `docs/evidence/screens/harness.png`
- `docs/evidence/screens/mcp.png`
- `docs/evidence/screens/project_ba.png`
- `docs/evidence/screens/project_bugs.png`
- `docs/evidence/screens/project_qe.png`
- `docs/evidence/screens/skills_list.png`
- `docs/evidence/screens/skills_studio.png`

## Not verified

- Every listed level executed tests.
