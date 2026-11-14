# Coverage map: prj_db07f1d16d2a

Written by the plugin's hooks from the documents on disk. Do not edit it: it is rebuilt after every change and checked at every gate.

| Gate | Check | Gaps |
|---|---|---|
| 1 | PASS | - |
| 2 | PASS | - |
| 3 | FAIL | cases the coverage auditor says do not cover their scenario: TC-APP-004 (PARTIAL), TC-APP-023 (PARTIAL), TC-APP-042 (PARTIAL) |
| 4 | FAIL | cases the coverage auditor says do not cover their scenario: TC-APP-004 (PARTIAL), TC-APP-023 (PARTIAL), TC-APP-042 (PARTIAL)<br>generated tests with no code confidence review: TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004, TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008, TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016, TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020, TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024, TC-APP-025 and 22 more<br>05-generation/confidence.json was not recorded from the confidence-reviewer agent<br>05-generation/audit.json missing: run the coverage-auditor agent on the generated tests |
| 5 | FAIL | cases the coverage auditor says do not cover their scenario: TC-APP-004 (PARTIAL), TC-APP-023 (PARTIAL), TC-APP-042 (PARTIAL)<br>generated tests with no code confidence review: TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004, TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008, TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016, TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020, TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024, TC-APP-025 and 22 more<br>05-generation/confidence.json was not recorded from the confidence-reviewer agent<br>05-generation/audit.json missing: run the coverage-auditor agent on the generated tests<br>designed cases with no test result (0 of 47 executed): TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004, TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008, TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016, TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020, TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024, TC-APP-025 and 22 more |

Requirements 13 · plan scenarios 12 · designed cases 47 · test files 47 · results 0

| Scenario | Area | Level | Requirements | Cases | Tests | Results |
|---|---|---|---|---|---|---|
| SC-AREA-001-001 | Health endpoint returns status and tool count | Integration | REQ-001 | TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004 | 4/4 | -, -, -, - |
| SC-AREA-002-001 | Run calculator - invalid JSON body returns 400 | Integration | REQ-003 | TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008 | 4/4 | -, -, -, - |
| SC-AREA-003-001 | Run calculator - invalid sanitized params returns 400 | Integration | REQ-005 | TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012 | 4/4 | -, -, -, - |
| SC-AREA-004-001 | Run calculator - calculator domain errors return 400 | Integration | REQ-006 | TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016 | 4/4 | -, -, -, - |
| SC-AREA-005-001 | Run calculator - unexpected exception returns 400 | Integration | REQ-007 | TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020 | 4/4 | -, -, -, - |
| SC-AREA-006-001 | Run calculator - valid input returns 200 and result | Integration | REQ-008 | TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024 | 4/4 | -, -, -, - |
| SC-AREA-007-001 | API NAV - invalid scheme code returns 400 | Integration | REQ-009 | TC-APP-025, TC-APP-026, TC-APP-027 | 3/3 | -, -, - |
| SC-AREA-008-001 | API NAV - invalid query length returns 400 | Integration | REQ-010 | TC-APP-028, TC-APP-029, TC-APP-030, TC-APP-031 | 4/4 | -, -, -, - |
| SC-AREA-009-001 | API FX - invalid currency codes return 400 | Integration | REQ-011 | TC-APP-032, TC-APP-033, TC-APP-034, TC-APP-035 | 4/4 | -, -, -, - |
| SC-AREA-010-001 | API Quote - invalid symbol returns 400 | Integration | REQ-012 | TC-APP-036, TC-APP-037, TC-APP-038, TC-APP-039 | 4/4 | -, -, -, - |
| SC-AREA-011-001 | Payload size limit on all /api endpoints | Integration | REQ-013 | TC-APP-040, TC-APP-041, TC-APP-042, TC-APP-043 | 4/4 | -, -, -, - |
| SC-AREA-012-001 | Security headers on every HTTP response | Integration | REQ-015 | TC-APP-044, TC-APP-045, TC-APP-046, TC-APP-047 | 4/4 | -, -, -, - |
