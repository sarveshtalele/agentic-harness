# P2 evidence notes (2026-11-10)

| Check | Result |
|---|---|
| Offline suite | 597 passed, 0 failed (REPORT.md) |
| Harness tests (`tests/test_maf_harness.py`, ScriptedClient) | 5 passed: skills offered by name only and body only via `load_skill`; todos persist across turns on disk; every tool call in `tool_calls` and none logged refused; per-call history on disk and one `agent_calls` row per round; nothing written to the process cwd |
| Live (`tests/test_maf_harness_live.py`, real model deepseek-v4-flash-global through the configured proxy) | 1 passed: the model called `load_skill` and `todos_add`, telemetry recorded 3 model calls, two todos stored |
| Real UI (`/chat/<project>`, Playwright Chromium against the running app) | "Project harness" offered; a harness chat starts; with no model in the throwaway preview database the pane shows "No model configured. Open Settings…" (honest error, no invented reply). Screenshot `../2026-11-10-p2-harness/harness_chat.png` |
| Found by running | CopilotKit route had a hardcoded agent list ("harness" and "bug-fix-reviewer" crashed the page); streamed harness calls were not recorded by telemetry. Both fixed and covered by tests |
| tsc / eslint | 0 errors / 0 problems |

## Not verified

- The real model through the browser UI (the preview database has no model; a real key is not typed into Settings by the agent).
- Smoke and E2E levels (Next.js production build cannot bind a local port in this environment).
- Windows and Linux runs (CI after push).
