---
name: comprehensive-quality-strategy-test-plan-agent-skill
description: "Automated specification enforcement and verification operations grounded on Comprehensive Quality Strategy & Test Plan (v1). Grounded in project specifications and requirements."
metadata:
  author: "admin"
  version: "1.4.0"
  category: "quality-engineering"
  tags: "agent-skill, comprehensive-quality-strategy-test-plan-agent-skill, maf-2.0"
---

# Comprehensive Quality Strategy & Test Plan Agent Skill

Automated specification enforcement and verification operations grounded on Comprehensive Quality Strategy & Test Plan (v1).

## Capabilities & Scope
- Grounded execution of domain workflows according to enterprise verification rules.
- Automated parameter validation, error handling, and structured evidence logging.

## Core Operational Workflow (Step-by-Step Checklist)
1. **Ingest test scenario matrix & priority classifications (P0-P2) for Comprehensive Quality Strategy & Test Plan**
2. **Synthesize deterministic test fixtures & synthetic datasets**
3. **Execute test cases in bounded sandbox worktree**
4. **Collect pass/fail execution logs and stack traces**
5. **Compute gate pass rate and trace coverage matrix**

## Quality & Security Guardrails
- **Sandboxed Execution**: Runs in isolated subshell with sanitized environment.
- **Deterministic**: Returns structured JSON responses with zero hallucinations.
- **Zero-Trust**: Does not permit unauthorized shell escapes or unvetted network calls.


### Grounding Specification (Comprehensive Quality Strategy & Test Plan v1):
The test plan focuses on the backend API (FastAPI) as the primary interface, with no E2E tests due to the absence of a browser-based UI. Unit tests validate core logic and error handling, integration tests verify API endpoints and database interactions, and I/O logic is tested at the integration level. Pytest is the standard framework for Python and is already present in the repository.

| Area | Requirements | Risk | Level | Framework | Rationale |
|---|---|---|---|---|---|
| Data tool DataError handling | REQ-020 | P1 | Unit | pytest | Pure logic testing: verify that a function raising DataError returns a dict with error field, no I/O. |
| Filtered paginated call history | REQ-001 | P1 | Integration | pytest | API boundary: test GET /observability/calls with query parameters, verify JSON response structure and pagination fields. |
| Observability summary | REQ-002 | P1 | Integration | pytest | API boundary: test GET /observability/summary for correct fields (counts, error rate, latencies). |
| SSE stream for new MCP calls | REQ-003 | P1 | Integration | pytest | Service boundary: test GET /observability/stream returns StreamingResponse with correct media type and cache headers. |
| Server status surface | REQ-004 | P1 | Integration | pytest | API boundary: test GET /observability/servers for JSON structure with server, gateway, callers_seen, live_listeners. |
| Raw gateway log tail | REQ-005 | P1 | Integration | pytest | API boundary: test GET /observability/gateway-logs/raw returns PlainTextResponse with concatenated log content. |
| Get tool allowlist policy | REQ-006 | P1 | Integration | pytest | API boundary: test GET /observability/policy for JSON with editable, config_path, tools, orphaned fields. |
| Update tool allowlist policy | REQ-007 | P1 | Integration | pytest | API boundary: test PUT /observability/policy with valid body, verify restart_required: true in response. |
| Reject policy update when editing disabled | REQ-008 | P1 | Integration | pytest | API boundary: test PUT /observability/policy returns 403 when disabled, using dependency mocking. |
| Reject policy update with unknown tools | REQ-009 | P1 | Integration | pytest | API boundary: test PUT /observability/policy returns 400 for non-disabled PolicyError. |
| List companies with filters | REQ-010 | P1 | Integration | pytest | API boundary: test GET /listings/companies with sector, market, active_only filters, verify JSON array. |
| Get company by symbol | REQ-011 | P1 | Integration | pytest | API boundary: test GET /listings/companies/{symbol} for existing symbol returns company JSON; test 404 for missing symbol. |
| List sectors with company counts | REQ-012 | P1 | Integration | pytest | API boundary: test GET /listings/sectors for JSON array with sector and company_count fields. |
| Get filings for a symbol | REQ-013 | P1 | Integration | pytest | API boundary: test GET /filings/{symbol} returns array or 404 if no filings (database query). |
| Get latest filing for a symbol | REQ-014 | P1 | Integration | pytest | API boundary: test GET /filings/{symbol}/latest returns single filing or 404. |
| AG-UI chat endpoint | REQ-015 | P1 | Integration | pytest | API boundary: test POST /agui returns StreamingResponse with correct headers (text/event-stream, X-Accel-Buffering: no). |
| AG-UI capabilities endpoint | REQ-016 | P1 | Integration | pytest | API boundary: test GET /agui/capabilities for JSON with declared, gateway_url, gateway_connected fields. |
| Health check endpoint | REQ-017 | P1 | Integration | pytest | API boundary: test GET /health for JSON object with all required fields. |
| Root endpoint with service info | REQ-018 | P1 | Integration | pytest | API boundary: test GET / returns JSON with service name, protocol_version, docs URL, mcp path, modules list. |
| MCP GET/DELETE returns 405 | REQ-019 | P1 | Integration | pytest | API boundary: test GET and DELETE on MCP path return HTTP 405 with JSON-RPC error. |
