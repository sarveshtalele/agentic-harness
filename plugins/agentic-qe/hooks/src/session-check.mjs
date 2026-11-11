// Plain JavaScript (no TypeScript syntax) so it still runs on Node 16+, where session-check.ts cannot load.
const [maj, min] = process.versions.node.split(".").map(Number);
if (maj < 22 || (maj === 22 && min < 18)) {
  console.log(JSON.stringify({
    hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: "agentic-qe hooks need Node 22.18+; guardrails are not active" }
  }));
} else {
  import("./session-check.ts").then((m) => m.run()).catch(() => {});
}
