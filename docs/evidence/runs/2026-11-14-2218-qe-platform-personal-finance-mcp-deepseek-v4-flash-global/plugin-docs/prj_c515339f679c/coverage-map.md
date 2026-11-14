# Coverage map: prj_c515339f679c

Written by the plugin's hooks from the documents on disk. Do not edit it: it is rebuilt after every change and checked at every gate.

| Gate | Check | Gaps |
|---|---|---|
| 1 | PASS | - |
| 2 | PASS | - |
| 3 | FAIL | plan scenarios with no designed case (12 of 16 designed): SC-I-011-001, SC-I-012-001, SC-I-013-001, SC-I-014-001<br>cases the coverage auditor says do not cover their scenario: TC-APP-004 (PARTIAL), TC-APP-008 (PARTIAL), TC-APP-015 (PARTIAL), TC-APP-021 (PARTIAL), TC-APP-022 (PARTIAL) |
| 4 | FAIL | plan scenarios with no designed case (12 of 16 designed): SC-I-011-001, SC-I-012-001, SC-I-013-001, SC-I-014-001<br>cases the coverage auditor says do not cover their scenario: TC-APP-004 (PARTIAL), TC-APP-008 (PARTIAL), TC-APP-015 (PARTIAL), TC-APP-021 (PARTIAL), TC-APP-022 (PARTIAL)<br>generated tests with no code confidence review: TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004, TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008, TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016, TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020, TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024, TC-APP-025 and 15 more<br>05-generation/confidence.json was not recorded from the confidence-reviewer agent<br>05-generation/audit.json missing: run the coverage-auditor agent on the generated tests |
| 5 | FAIL | plan scenarios with no designed case (12 of 16 designed): SC-I-011-001, SC-I-012-001, SC-I-013-001, SC-I-014-001<br>cases the coverage auditor says do not cover their scenario: TC-APP-004 (PARTIAL), TC-APP-008 (PARTIAL), TC-APP-015 (PARTIAL), TC-APP-021 (PARTIAL), TC-APP-022 (PARTIAL)<br>generated tests with no code confidence review: TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004, TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008, TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016, TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020, TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024, TC-APP-025 and 15 more<br>05-generation/confidence.json was not recorded from the confidence-reviewer agent<br>05-generation/audit.json missing: run the coverage-auditor agent on the generated tests<br>designed cases with no test result (0 of 40 executed): TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004, TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008, TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-015, TC-APP-016, TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020, TC-APP-021, TC-APP-022, TC-APP-023, TC-APP-024, TC-APP-025 and 15 more |

Requirements 13 · plan scenarios 16 · designed cases 40 · test files 40 · results 0

| Scenario | Area | Level | Requirements | Cases | Tests | Results |
|---|---|---|---|---|---|---|
| SC-U-001-001 | Calculator input validation: bounds and caps (pure logic) | Unit | REQ-005, REQ-006 | TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014, TC-APP-033, TC-APP-034, TC-APP-035, TC-APP-036 | 8/8 | -, -, -, -, -, -, -, - |
| SC-U-002-001 | Scheme code validation (pure logic) | Unit | REQ-009 | TC-APP-021, TC-APP-022 | 2/2 | -, - |
| SC-U-003-001 | Query length validation (pure logic) | Unit | REQ-010 | TC-APP-023, TC-APP-024 | 2/2 | -, - |
| SC-U-004-001 | Currency code regex validation (pure logic) | Unit | REQ-011 | TC-APP-025, TC-APP-026 | 2/2 | -, - |
| SC-U-005-001 | Symbol regex validation (pure logic) | Unit | REQ-012 | TC-APP-027, TC-APP-028 | 2/2 | -, - |
| SC-I-006-001 | Health check endpoint | Integration | REQ-001 | TC-APP-001, TC-APP-002, TC-APP-003, TC-APP-004 | 4/4 | -, -, -, - |
| SC-I-007-001 | Tool listing endpoint | Integration | REQ-002 | TC-APP-005, TC-APP-006, TC-APP-007, TC-APP-008 | 4/4 | -, -, -, - |
| SC-I-008-001 | Calculator endpoint: malformed JSON body | Integration | REQ-003 | TC-APP-009, TC-APP-010 | 2/2 | -, - |
| SC-I-009-001 | Calculator endpoint: domain error wrapping | Integration | REQ-007 | TC-APP-015, TC-APP-016 | 2/2 | -, - |
| SC-I-010-001 | Calculator endpoint: unexpected exception hiding | Integration | REQ-008 | TC-APP-017, TC-APP-018, TC-APP-019, TC-APP-020 | 4/4 | -, -, -, - |
| SC-I-011-001 | NAV endpoint: invalid scheme code | Integration | REQ-009 | **none** | 0/0 | - |
| SC-I-012-001 | NAV endpoint: invalid query length | Integration | REQ-010 | **none** | 0/0 | - |
| SC-I-013-001 | FX endpoint: invalid currency code | Integration | REQ-011 | **none** | 0/0 | - |
| SC-I-014-001 | Quote endpoint: invalid symbol | Integration | REQ-012 | **none** | 0/0 | - |
| SC-I-015-001 | Request body size limit | Integration | REQ-013 | TC-APP-037, TC-APP-038, TC-APP-039, TC-APP-040 | 4/4 | -, -, -, - |
| SC-I-016-001 | Security headers present on every response | Integration | REQ-015 | TC-APP-029, TC-APP-030, TC-APP-031, TC-APP-032 | 4/4 | -, -, -, - |
