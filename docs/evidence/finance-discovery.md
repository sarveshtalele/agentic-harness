## Purpose and Users
This is a **Personal Finance MCP server** providing deterministic financial calculators exposed through the Model Context Protocol (MCP). It runs as an MCP server (stdio or SSE), a website with Next.js UI, and a hosted connector on Hugging Face. Users include anyone connecting via Claude Desktop, Claude Code, Cursor, or any MCP-compatible client, plus website visitors using the calculator, market dashboard, and tool catalog at `/tools`.

## How It Runs End to End
1. **User connects an MCP client** (e.g., Claude Desktop) to `https://host/mcp` (streamable-HTTP) or runs `python -m src` (stdio).
2. **Client calls a tool** — the request enters `src/server.py` which initializes `FastMCP("Personal Finance Advisor")` at line 30 and registers all 13 tool modules at lines 77-89.
3. **Tool dispatches** to the corresponding pure math function in `src/tools/*.py` — e.g., `src/tools/tvm.py:future_value`, wrapped by a `@mcp.tool` decorator that calls `src/utils/formatters.py:format_tool_response`.
4. **Result returns** as a formatted string through the MCP transport.
5. **Web server path** (`src/web/server.py`): uvicorn on port 7860 serves the Starlette app built at line 348 from `mcp.streamable_http_app()` plus JSON API routes (`/api/health`, `/api/tools`, `/api/calc`, `/api/nav`, `/api/fx`, `/api/quote`) and the static Next.js export (`web/out`).
6. **Docker deployment** (`Dockerfile`): multi-stage build compiles Next.js (stage 1), then installs the Python package with `pip install -e ".[web]"` and runs `python -m src.web` on port 7860 with a health check at `/api/health`.

## Architecture
```
┌─────────────┐    ┌─────────────────────────────────────────────┐
│ MCP Clients  │    │  Unified Server (single port)              │
│ (Claude,    │───▶│  src/web/server.py                          │
│  Cursor)    │    │  ┌──────────┐  ┌─────────┐  ┌───────────┐  │
└─────────────┘    │  │ /mcp     │  │ /api/*  │  │ / (static) │  │
                   │  │ (FastMCP │  │ (JSON   │  │ (Next.js  │  │
                   │  │  stream) │  │  API)   │  │   site)   │  │
                   │  └────┬─────┘  └────┬────┘  └───────────┘  │
                   └───────┼─────────────┼──────────────────────┘
                           │             │
                   ┌───────▼─────────────▼──────────────────────┐
                   │  src/tools/  (13 tool modules, pure math)  │
                   │  tvm.py  debt.py  planning.py  bonds.py   │
                   │  stocks.py  mutual_funds.py  portfolio.py  │
                   │  derivatives.py  india_savings.py          │
                   │  cashflow.py  risk_profile.py  advisor.py  │
                   │  marketdata.py                             │
                   └────────────────────────────────────────────┘
```

Layers:
- **Transport Layer**: stdio (`src/server.py`), SSE (`run_production.py`), streamable-HTTP (`src/web/server.py`)
- **Tool Layer**: 13 Python modules in `src/tools/` with pure math functions and `register(mcp)` wrappers
- **Model Layer**: `src/models/schemas.py` (Pydantic models), `src/models/enums.py`
- **Utility Layer**: `src/utils/formatters.py` for output formatting
- **Web Layer**: `src/web/server.py` (Starlette/ASGI), `web/` (Next.js static export)

## Modules

| Path | Responsibility | Dependencies |
| :--- | :--- | :--- |
| `src/server.py` | FastMCP server init, registers all 13 tool modules | `mcp`, all `src.tools.*` |
| `src/__main__.py` | Entrypoint for `python -m src` (stdio) | `src.server` |
| `src/web/server.py` | Unified ASGI app: /mcp, /api/*, static files | `starlette`, `uvicorn`, `mcp`, `src.tools.*` |
| `src/web/__main__.py` | Entrypoint for `python -m src.web` | `src.web.server` |
| `src/tools/tvm.py` | Time Value of Money: 10 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/debt.py` | Debt & Loans: 6 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/planning.py` | Financial Planning: 9 calculators | `mcp`, `src.utils.formatters`, `src.tools.tvm` |
| `src/tools/bonds.py` | Fixed Income: 6 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/stocks.py` | Equity Valuation: 5 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/mutual_funds.py` | Mutual Funds: 7 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/portfolio.py` | Portfolio Analytics: 11 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/derivatives.py` | Derivatives: 5 calculators | `mcp`, `src.utils.formatters`, `math` |
| `src/tools/india_savings.py` | Indian Small Savings: 9 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/cashflow.py` | Cash Flow & Budgeting: 3 calculators | `mcp`, `src.utils.formatters` |
| `src/tools/risk_profile.py` | Risk Profiling: 1 calculator | `mcp`, `src.utils.formatters` |
| `src/tools/advisor.py` | Meta-advisor: 1 orchestrator (`create_financial_plan`) | `mcp`, `src.utils.formatters` |
| `src/tools/marketdata.py` | Live market data: 4 tools | `mcp`, `httpx`, `src.utils.formatters` |
| `src/models/schemas.py` | Pydantic input models (12 classes) | `pydantic`, `src.models.enums` |
| `src/models/enums.py` | Enums (CompoundingFrequency, AnnuityType, etc.) | none |
| `src/utils/formatters.py` | Output formatting helpers | none |
| `web/` | Next.js frontend (static export) | next, react |
| `run_production.py` | SSE server runner (legacy) | `mcp` |

## Interfaces
- **MCP tools**: 77 tools registered via `@mcp.tool` decorators across 13 modules. Categories: Time Value of Money (10), Portfolio Analytics (11), Financial Planning (9), Small Savings India (9), Mutual Funds (7), Debt & Loans (6), Fixed Income (6), Derivatives (5), Equity Valuation (5), Live Market Data (4), Cash Flow & Budgeting (3), Risk Profiling (1), Advisor (1).
- **HTTP API routes** (from `src/web/server.py`): 6 routes — `/api/health` (GET), `/api/tools` (GET), `/api/calc` (POST), `/api/nav` (GET), `/api/fx` (GET), `/api/quote` (GET).
- **Web paths**: `/` (home), `/tools` (catalog), `/calculator`, `/dashboard`, `/connect`.
- **Entrypoints**: `python -m src` (stdio), `python -m src.web` (HTTP), `python run_production.py` (SSE), `personal-finance-mcp` console script from `pyproject.toml`.

## Data and Integrations
- **No database** — stateless; every call is independent.
- **Live market data** (`src/tools/marketdata.py`): mutual fund NAVs (AMFI), FX rates (Frankfurter/ECB), equity quotes (Yahoo Finance). No API keys required.
- **Failure behavior**: Not determined from evidence. The generic exception handler at `src/web/server.py:268-273` catches exceptions during calculator execution and returns a "calculation failed" message, but `src/tools/marketdata.py` source code was not fully inspected for HTTP timeout/error handling.

## Configuration and Deployment
- **Environment variables**: `PORT` (default 7860 for HF Spaces), `MCP_HOST` (default 127.0.0.1), `MCP_PORT` (default 8000).
- **Dependencies**: `mcp[cli]>=1.0.0`, `pydantic>=2.0.0`, `httpx>=0.27`. Optional: `starlette>=0.37`, `uvicorn>=0.30` (web), `pytest>=7.0` (dev).
- **Build**: hatchling via `pyproject.toml`, wheel packages `["src"]`.
- **CI/CD**: 4 workflows in `.github/workflows/` — `ci.yml`, `codeql.yml`, `hf-sync.yml` (auto-sync to Hugging Face Docker Space), `pypi-publish.yml`.
- **Deployment**: Docker multi-stage build (`Dockerfile`), Hugging Face Docker Space. Health check at `/api/health` every 30s, port 7860.

## Existing Tests
- **Test runner**: pytest (from `pyproject.toml` line 37).
- **Test files**: 12 test files detected by scan.
- **Test count discrepancy**: README line 9 claims "137 tests passing" (badge), while `pyproject.toml` line 203 says "119 tests". Neither figure is verifiable from the scan evidence, which only reports 12 test files. The actual count of test functions is not determined.
- **Coverage**: Not determined — there is no evidence whether the 12 test files cover all 77 tools or only a subset, nor what specific assertions or edge cases (division by zero, negative inputs, boundary conditions) are validated.
- **How to run**: `pytest -q` (from README line 203).

## Risks
- `src/web/server.py:94-106` — In-memory rate-limit tracking (`_hits: dict[str, deque]`) uses a dict that resets on restart. Under massive IP rotation, memory pressure could occur until `_MAX_TRACKED_IPS` (20,000) is hit and the dict is cleared. Works only for single-process deployment. The 20,000 IP limit is coded at line 96 but the evidence does not show it is testable or enforced at any intermediate threshold.
- `src/web/server.py:196-220` — The `_sanitize_params` function silently drops nulls and nested structures at line 219 without logging or reporting this to the caller, which could mask configuration errors. There is no evidence of any notification mechanism.
- `src/web/server.py:311-316` — CORS middleware allows all origins (`allow_origins=["*"]`), which is permissive for a production deployment.
- `src/tools/planning.py:721` and throughout `src/tools/planning.py` — Tool responses are constructed as raw f-strings with hardcoded formatting (e.g., lines 525-549, 599-628, 653-673, 697-722, 754-772) instead of using the structured `format_tool_response` from `src/utils/formatters.py`. The evidence does not show how many of the 77 tools deviate from the `format_tool_response` pattern — only `src/tools/planning.py` is confirmed to use raw f-strings in at least 5 of its 9 tools. Other tool modules may also deviate; this is not determined.
- `src/tools/marketdata.py` — External API calls to AMFI/Frankfurter/Yahoo are made without API keys. The evidence does not document how HTTP timeouts, connection errors, or unexpected response formats are handled. The generic exception handler at `src/web/server.py:268-273` only covers the calculator API path, not the MCP tool path for `marketdata` tools.
- `src/server.py:30-72` — Tool descriptions and routing instructions embedded as FastMCP `instructions` string are long (lines 32-63) and tightly coupled to the codebase. Any mismatch between these instructions and actual tool behavior could cause incorrect LLM routing.

## Not Determined
- Whether the 12 test files cover all 77 tools or only a subset — no test file contents were inspected.
- What specific assertions or edge cases the tests validate (e.g., division by zero, negative inputs, boundary conditions, market data failure modes).
- Actual test function count — README claims 137, `pyproject.toml` line 203 says 119, scan reports 12 test files. These figures are contradictory and unverifiable from evidence.
- How `src/tools/marketdata.py` handles HTTP timeouts, connection errors, or unexpected response formats from external APIs — the full source was not provided.
- How many of the 77 tools use raw f-strings versus `format_tool_response` — only `src/tools/planning.py` is confirmed to deviate in at least 5 tools.
- Whether the 20,000 IP limit in `src/web/server.py:96` is enforced progressively or only as a hard clear — and whether it is testable.
- Whether the Next.js static export (`web/out`) has its own test suite.
- The contents of `docs/` directory (architecture, testing, deployment documentation).