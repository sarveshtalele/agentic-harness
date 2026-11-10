import { HttpAgent } from "@ag-ui/client";
import { CopilotRuntime, createCopilotRuntimeHandler } from "@copilotkit/runtime/v2";

const backend = process.env.ATLAS_BACKEND_URL || "http://127.0.0.1:8000";

// The chat agents come from the backend (src/backend/maf/agents, the ones with chat tools), the same list the agent
// picker shows. A hardcoded copy here drifted: "harness" and "bug-fix-reviewer" were offered but unknown, which crashed the chat.
async function chatAgentKeys(headers: Record<string, string>): Promise<string[]> {
  const response = await fetch(`${backend}/api/chat/agents`, { headers, cache: "no-store" });
  if (!response.ok) throw new Error(`Could not load chat agents from the backend: HTTP ${response.status}`);
  const agents: { key: string }[] = await response.json();
  return agents.map((agent) => agent.key);
}

// a runtime per request, because each chat call must carry the caller's session to the backend
async function handle(request: Request) {
  const headers = { cookie: request.headers.get("cookie") || "" };
  const keys = await chatAgentKeys(headers);
  const runtime = new CopilotRuntime({
    agents: Object.fromEntries(keys.map((key) => [key, new HttpAgent({ url: `${backend}/agui/${key}`, headers })])),
  });
  return createCopilotRuntimeHandler({ runtime, basePath: "/api/copilotkit" })(request);
}

export const GET = handle;
export const POST = handle;
