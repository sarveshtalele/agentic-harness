# Coverage map: prj_2989e94ccb67

Written by the plugin's hooks from the documents on disk. Do not edit it: it is rebuilt after every change and checked at every gate.

| Gate | Check | Gaps |
|---|---|---|
| 1 | PASS | - |
| 2 | PASS | - |
| 3 | FAIL | plan scenarios with no designed case (0 of 9 designed): SC-UNIT-PORTFOLIO-ERRORS-001, SC-UNIT-SANITIZE-PARAMS-001, SC-INTEGRATION-HEALTH-001, SC-INTEGRATION-CALC-ERRORS-001, SC-INTEGRATION-SECURITY-PAYLOAD-RATE-001, SC-INTEGRATION-SECURITY-HEADERS-001, SC-INTEGRATION-NAV-VALIDATION-001, SC-INTEGRATION-FX-VALIDATION-001, SC-INTEGRATION-QUOTE-VALIDATION-001 |
| 4 | FAIL | plan scenarios with no designed case (0 of 9 designed): SC-UNIT-PORTFOLIO-ERRORS-001, SC-UNIT-SANITIZE-PARAMS-001, SC-INTEGRATION-HEALTH-001, SC-INTEGRATION-CALC-ERRORS-001, SC-INTEGRATION-SECURITY-PAYLOAD-RATE-001, SC-INTEGRATION-SECURITY-HEADERS-001, SC-INTEGRATION-NAV-VALIDATION-001, SC-INTEGRATION-FX-VALIDATION-001, SC-INTEGRATION-QUOTE-VALIDATION-001 |
| 5 | FAIL | plan scenarios with no designed case (0 of 9 designed): SC-UNIT-PORTFOLIO-ERRORS-001, SC-UNIT-SANITIZE-PARAMS-001, SC-INTEGRATION-HEALTH-001, SC-INTEGRATION-CALC-ERRORS-001, SC-INTEGRATION-SECURITY-PAYLOAD-RATE-001, SC-INTEGRATION-SECURITY-HEADERS-001, SC-INTEGRATION-NAV-VALIDATION-001, SC-INTEGRATION-FX-VALIDATION-001, SC-INTEGRATION-QUOTE-VALIDATION-001 |

Requirements 26 · plan scenarios 9 · designed cases 0 · test files 0 · results 0

| Scenario | Area | Level | Requirements | Cases | Tests | Results |
|---|---|---|---|---|---|---|
| SC-UNIT-PORTFOLIO-ERRORS-001 | Portfolio calculation edge cases (zero divisors, dimension mismatches) | Unit | REQ-015, REQ-016, REQ-017, REQ-018, REQ-019, REQ-020 | **none** | 0/0 | - |
| SC-UNIT-SANITIZE-PARAMS-001 | Parameter sanitization validator (_sanitize_params) | Unit | REQ-021, REQ-022, REQ-023, REQ-024, REQ-025 | **none** | 0/0 | - |
| SC-INTEGRATION-HEALTH-001 | Health endpoint (/api/health) | Integration | REQ-001 | **none** | 0/0 | - |
| SC-INTEGRATION-CALC-ERRORS-001 | Calculator endpoint error handling (/api/calc) | Integration | REQ-003, REQ-004, REQ-005, REQ-006, REQ-007 | **none** | 0/0 | - |
| SC-INTEGRATION-SECURITY-PAYLOAD-RATE-001 | Security: payload size limit and rate limiting | Integration | REQ-008, REQ-009 | **none** | 0/0 | - |
| SC-INTEGRATION-SECURITY-HEADERS-001 | Security headers on all responses | Integration | REQ-010 | **none** | 0/0 | - |
| SC-INTEGRATION-NAV-VALIDATION-001 | NAV endpoint parameter validation (/api/nav) | Integration | REQ-011, REQ-012 | **none** | 0/0 | - |
| SC-INTEGRATION-FX-VALIDATION-001 | FX endpoint currency code validation (/api/fx) | Integration | REQ-013 | **none** | 0/0 | - |
| SC-INTEGRATION-QUOTE-VALIDATION-001 | Quote endpoint symbol validation (/api/quote) | Integration | REQ-014 | **none** | 0/0 | - |
