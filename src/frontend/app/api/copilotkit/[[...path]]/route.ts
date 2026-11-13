import { HttpAgent } from "@ag-ui/client";
import { CopilotRuntime, createCopilotRuntimeHandler } from "@copilotkit/runtime/v2";

// No usage data to third parties: next.config sets this only while building, and the standalone server reads the
// environment at run time.
process.env.COPILOTKIT_TELEMETRY_DISABLED = "true";
const backend = process.env.ATLAS_BACKEND_URL || "http://127.0.0.1:8000";
// A chat request is a few messages; anything far larger is refused before any library parses it (zod 3 inside CopilotKit
// has a known memory exhaustion on oversized input, GHSA-mrhx-c7xc-m3w5).
const MAX_BODY_BYTES = 2 * 1024 * 1024;

// The chat agents come from the backend (src/backend/maf/agents, the ones with chat tools), the same list the agent
// picker shows. A hardcoded copy here drifted: "harness" and "bug-fix-reviewer" were offered but unknown, which crashed the chat.
// The backend also checks the caller's session first, so nobody who is signed out reaches the runtime.
async function chatAgentKeys(headers: Record<string, string>): Promise<string[] | Response> {
  let response: Response;
  try {
    response = await fetch(`${backend}/api/chat/agents`, { headers, cache: "no-store" });
  } catch {
    return new Response(`The backend did not answer at ${backend}. Start it, or set ATLAS_BACKEND_URL to its address.`, { status: 502 });
  }
  if (response.status === 401 || response.status === 403) return new Response("Sign in first", { status: response.status });
  if (!response.ok) return new Response(`Could not load chat agents from the backend: HTTP ${response.status}`, { status: 502 });
  const agents: { key: string }[] = await response.json();
  return agents.map((agent) => agent.key);
}

// a runtime per request, because each chat call must carry the caller's session to the backend
async function handle(request: Request) {
  if (Number(request.headers.get("content-length") || 0) > MAX_BODY_BYTES) return new Response("Request too large", { status: 413 });
  const headers = { cookie: request.headers.get("cookie") || "" };
  const keys = await chatAgentKeys(headers);
  if (keys instanceof Response) return keys;
  const runtime = new CopilotRuntime({
    agents: Object.fromEntries(keys.map((key) => [key, new HttpAgent({ url: `${backend}/agui/${key}`, headers })])),
  });
  return createCopilotRuntimeHandler({ runtime, basePath: "/api/copilotkit" })(request);
}

export const GET = handle;
export const POST = handle;
