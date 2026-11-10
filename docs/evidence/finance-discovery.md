## Purpose and Users
A deterministic personal-finance toolkit exposed as an MCP (Model Context Protocol) server. The README states it provides 77 calculators covering time value of money, debt management, Indian small-savings schemes (PPF/SSY/NSC/KVP/SCSS/RD/FD/EPF), stock/bond valuation, derivatives, mutual funds, portfolio analytics, risk profiling, cash flow analysis, financial planning, and live market data (mutual fund NAVs, FX rates, equity quotes). An `create_financial_plan` orchestrator chains tools to produce prioritized financial plans from plain-language user stories.

It runs three ways from one codebase, per the README:
- As an MCP server connected to Claude Desktop, Claude Code, Cursor, or any MCP client
- As a website with a Next.js UI (calculator, market dashboard, tool catalog)
- As a hosted connector deployed to a Hugging Face Docker Space

Users are individuals seeking financial planning insights, LLM applications using MCP tools, and developers integrating finance calculators.

## How It Runs End to End

**MCP server (stdio transport):**
1. Entry: `src/__main__.py` calls `src/server.py:main()` (line 92)
2. `src/server.py` initializes `FastMCP` ("Personal Finance Advisor") at line 30 and registers all tool modules via their `register(mcp)` functions at lines 77-89
3. `mcp.run(transport="stdio")` at line 94 listens for JSON-RPC requests on stdin/stdout
4. A tool call like `calculate_net_worth` is dispatched to the pure function in `src/tools/planning.py:calculate_net_worth()` (line 16)
5. Results are returned via the MCP protocol

**MCP server (SSE transport):**
1. Entry: `run_production.py:main()` calls `src.server:mcp.run(transport="sse")` at line 43 on `MCP_HOST`:`MCP_PORT`
2. Same tool registration as stdio; responses stream over SSE at `/sse`

**Unified web server (Hugging Face deployment):**
1. Entry: `src/web/__main__.py` calls `src/web/server.py:main()` at line 2
2. `build_app()` in `src/web/server.py` (line 306) takes `mcp.streamable_http_app()` and adds API routes and static file serving
3. A POST to `/api/calc` with calculator parameters is handled by `run_calc()` at line 243, which looks up the calculator in `CALCULATORS` dict (lines 37-53) and calls the pure function

## Architecture

```
src/
├── server.py            # FastMCP server — registers all tool modules
├── __main__.py          # `python -m src` (stdio transport)
├── tools/               # pure math fns + per-module register(mcp)
│   ├── tvm.py           debt.py  planning.py  bonds.py  stocks.py  
│   ├── mutual_funds.py  portfolio.py  derivatives.py  india_savings.py  
│   ├── cashflow.py      risk_profile.py  advisor.py    marketdata.py
├── models/              # Pydantic schemas + enums
├── utils/               # output formatters
└── web/                 # unified Starlette server (MCP + /api + static site)
    ├── server.py        # routes, security middleware, calculator registry
    └── __main__.py      # `python -m src.web` (uvicorn, port 7860)

web/                     # Next.js front-end (static export → web/out)
└── app/                 # home, tools, calculator, dashboard, connect
```

## Modules

| Path | Responsibility | Depends On |
|---|---|---|
| `src/server.py` | FastMCP initialization, tool registration, `main()` for stdio transport | All tool modules, `mcp`, `mcp.server.fastmcp`, `mcp.server.transport_security` |
| `src/__main__.py` | Entry point for `python -m src` (stdio) | `src.server` |
| `src/web/server.py` | Unified ASGI app: MCP streamable-http + JSON API + static site | `mcp`, `starlette`, `src.tools.*` |
| `src/web/__main__.py` | Entry point for `python -m src.web` (web server) | `src.web.server` |
| `src/tools/planning.py` | Net worth, financial ratios, emergency fund, budget, health score, goal/retirement/education/insurance planning | `src.tools.tvm`, `src.utils.formatters` |
| `src/tools/portfolio.py` | CAPM, Sharpe/Sortino/Treynor/Jensen ratios, MPT risk/return, two-asset portfolio, allocation suggestions | `src.utils.formatters` |
| `src/tools/tvm.py` | TVM calculators (future/present value, annuity, perpetuity, EAR, rule of 72, real return) | `src.utils.formatters` |
| `src/tools/debt.py` | EMI, loan amortization, prepayment, consolidation, invest-vs-prepay | `src.utils.formatters` |
| `src/tools/mutual_funds.py` | SIP, SWP, CAGR, NAV, lumpsum-vs-SIP, expense ratio impact | `src.utils.formatters` |
| `src/tools/india_savings.py` | PPF, SSY, NSC, KVP, SCSS, RD, FD, EPF, gratuity calculators | `src.utils.formatters` |
| `src/tools/bonds.py` | Bond price, YTM, duration, convexity, zero-coupon pricing | `src.utils.formatters` |
| `src/tools/derivatives.py` | Futures fair value, option payoff, put-call parity, Black-Scholes, beta hedge | `src.utils.formatters` |
| `src/tools/stocks.py` | DDM (Gordon growth, multi-stage), P/E, DCF, dividend yield | `src.utils.formatters` |
| `src/tools/cashflow.py` | Cash flow statement, debt-to-income, contingency fund | `src.utils.formatters` |
| `src/tools/risk_profile.py` | Risk profile score, suggested equity/debt split | `src.utils.formatters` |
| `src/tools/advisor.py` | `create_financial_plan` orchestrator — maps user story to chained tools | All planning modules, `src.utils.formatters` |
| `src/tools/marketdata.py` | Live: MF search, NAV (AMFI), FX rates (Frankfurter/ECB), quotes (Yahoo) | `httpx` |
| `src/models/schemas.py` | Pydantic input models (TVM, annuity, loan, goal, net worth, budget, bond, stock, portfolio, SIP, retirement, health) | `pydantic`, `src.models.enums` |
| `src/models/enums.py` | Enums (CompoundingFrequency, AnnuityType, LoanType, RiskProfile, BondType, ReturnMethod) | None |
| `src/utils/formatters.py` | Output formatting (currency, percentage, table, tool response) | None |
| `run_production.py` | SSE transport runner with CLI/env config | `src.server` |

## Interfaces

**MCP tools:** Tool modules are registered via `src/server.py` lines 77-89 calling `register(mcp)` on each module. The scan shows 13 tool files with exported symbols. The README claims 77 tools. Key functions extracted from the scan include:
- From `src/tools/planning.py`: `calculate_net_worth`, `calculate_financial_ratios`, `emergency_fund_calculator`, `budget_analysis`, `financial_health_score`, `register`
- From `src/tools/portfolio.py`: `portfolio_expected_return`, `portfolio_risk`, `two_asset_portfolio`, `capm`, `sharpe_ratio`, `treynor_ratio`, `jensens_alpha`, `information_ratio`, `sortino_ratio`, `asset_allocation_suggestion`
- From `src/tools/tvm.py`: `future_value`, `present_value`, `future_value_annuity`, `present_value_annuity`, `perpetuity_value`, `rule_of_72`, `effective_annual_rate`, `real_rate_of_return`, `inflation_adjusted_amount`, `required_monthly_savings`
- From `src/tools/marketdata.py`: `search_mutual_funds`, `get_mf_nav`, `get_fx_rate`, `get_quote`, `register`

**JSON API routes (defined in `src/web/server.py` lines 320-326):**
- `GET /api/health` — health check
- `GET /api/tools` — tool catalog
- `POST /api/calc` — run calculator
- `GET /api/nav` — mutual fund NAV
- `GET /api/fx` — FX rate
- `GET /api/quote` — stock quote

**MCP protocol:** Three transports: stdio, SSE (via `run_production.py`), streamable-HTTP (via web server at `/mcp`)

**CLI:** `personal-finance-mcp` (defined in `pyproject.toml` scripts) runs the stdio MCP server.

## Data and Integrations

**External services** (from `src/tools/marketdata.py` symbols): The search_mutual_funds, get_mf_nav, get_fx_rate, and get_quote functions use `httpx` to call public APIs. The README states these are keyless public sources (AMFI, Frankfurter/ECB, Yahoo Finance).

**Internal data:** All calculations are pure functions. No database, no sessions, no persistent state. Input validation exists in `_sanitize_params()` in `src/web/server.py` but only the first 22 lines of that file are visible in the evidence.

## Configuration and Deployment

**Environment variables** (from `run_production.py` lines 18-19 and `src/web/server.py` line 354):
- `MCP_HOST` — SSE bind host (default: `127.0.0.1`)
- `MCP_PORT` — SSE bind port (default: `8000`)
- `PORT` — web server port (default: `7860`)

**CI/CD** (from scan): 4 workflows at `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `.github/workflows/hf-sync.yml`, `.github/workflows/pypi-publish.yml`

**Dockerfile:** Multi-stage build. Stage 1 uses `node:20-slim` to build Next.js site. Stage 2 uses `python:3.12-slim`, installs the Python package, copies static files, exposes port 7860 with a health check hitting `/api/health`.

**pyproject.toml:** Package `personal-finance-mcp` v2.0.0, Python >=3.10. Dependencies: `mcp[cli]`, `pydantic`, `httpx`. Optional: `web` = `starlette`, `uvicorn`; `dev` = `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`. Build system: hatchling.

## Existing Tests

12 test files detected by the scan. Test runner is `pytest`, configured in `pyproject.toml` with `testpaths = ["tests"]` and `pythonpath = ["."]`. The README claims "119 tests" and "137 passing" but no test execution output is provided in the evidence. Coverage and completeness cannot be verified.

## Risks

1. **Input validation scope limited** — From `src/tools/planning.py` lines 429-442, the `calculate_net_worth_tool` MCP tool accepts `assets_json` and `liabilities_json` as raw strings and calls `json.loads()` on them. Any malformed or unexpected JSON input will raise an exception. The `_sanitize_params()` validation in `src/web/server.py` applies to the JSON API path only, not the MCP tool path.

2. **Rate limiting scope** — The scan evidence is insufficient to determine whether rate limiting applies to the MCP streamable-HTTP endpoint or only to `/api` paths.

3. **External API dependencies** — `src/tools/marketdata.py` depends on three external services (AMFI, ECB/Frankfurter, Yahoo Finance). Any service change or outage will cause tool failures. No fallback or caching is visible in the evidence.

4. **In-memory state for rate limiting** — The evidence shows `src/web/server.py` implements some form of per-IP tracking (line 95 references `_hits` dict with `deque`), but the full implementation is not visible. Memory exhaustion from spoofed/rotating IPs is a theoretical risk.

5. **`create_financial_plan` orchestrator dependency chain** — `src/tools/advisor.py` imports from all other planning tools. Any module import failure will prevent the advisor tool and potentially the entire server from starting.

6. **The evidence is incomplete** for verifying security middleware, rate limiting, body caps, and security headers. These claims are made in the README and code documentation but only partial code (first 22 lines of `src/web/server.py`) was provided.

## Not Determined
- Exact tool count (77 claimed) cannot be verified from the evidence — no full tool registry enumeration is shown
- Test execution results or pass/fail counts — the README claims 119/137 tests but no test output is in evidence
- Test coverage percentages or individual test file contents
- Full implementation of `src/web/server.py` SecurityMiddleware, rate limiting, body caps, and security headers — only first 22 lines provided
- Performance benchmarks or scaling characteristics
- Authentication or authorization mechanism (none present in code)
- Content of documentation files (`docs/`)
- Content of Next.js front-end code
- How `mcp.streamable_http_app()` is implemented (external library)
- Version pinning or compatibility with specific `mcp` library versions
- Error handling details for all tool functions