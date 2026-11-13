# Model proxy does not pass the request's tools (2026-11-13)

Endpoint: the LiteLLM proxy configured in Settings (`litellm-proxy-app-…eastus2-01.azurewebsites.net`). Every probe sent
fresh, uniquely named tools and a unique prompt, directly with `httpx` (no platform code in between). No key is recorded.

| Probe | Result |
|---|---|
| gpt-4.1, 3 tools `alpha_tool`, `beta_tool`, `gamma_tool`, "list your tools" | answered `list_files`, `read_file`, `grep` (tools from earlier platform requests) |
| gpt-4.1, `tool_choice: required`, tools `alpha_tool`, `beta_tool` | called `list_files`, a tool not in the request |
| 6 models, one unique `save_<hex>` tool, streamed and not streamed | none called it; all said the only tool is `read_file`; deepseek called `read_file` |
| 30 unique tools `t<hex>_<n>`, streamed, per model | gpt-5 correct once; o3 then returned `tcdde_13`, a name from the earlier gpt-5 request |
| same, with `Cache-Control: no-cache` and LiteLLM `"cache": {"no-cache": true, "no-store": true}` | gpt-5 and deepseek again returned the stale `tcdde_13` |

Conclusion: the proxy reuses tool definitions (and at least once a response) from earlier requests instead of the ones
in the request. An agent then sees tools it does not have and misses the ones it has; turns end empty or call the wrong
tool. This explains the empty requirements turns of the gpt-5 QE cycle run (`../2026-11-13-qe-cycle-g5-gpt-5/`) and
erratic harness behaviour, and cannot be fixed from the client. The proxy's configuration needs checking: response or
semantic caching keyed without the tools, or a pre-call hook that rewrites `tools`.
