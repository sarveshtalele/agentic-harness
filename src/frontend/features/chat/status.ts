/** Plain-words status lines for the harness, derived only from real AG-UI events (plan M4, US-60). */

const PHRASES: Record<string, string> = {
  scan_repository: "Analysing the repository",
  run_tests: "Running tests",
  save_document: "Creating document",
  start_workflow: "Starting workflow",
  grep: "Searching the code",
  find_tools: "Finding tools",
  load_tools: "Loading tools",
};

export const THINKING = "Thinking";
export const WRITING = "Writing";

/** The line for a tool call. `args` are its parsed arguments once TOOL_CALL_END arrives; before that only the name is known. */
export function toolStatus(name: string, args: Record<string, unknown> = {}): string {
  const arg = (key: string) => (typeof args[key] === "string" && args[key] ? ` ${args[key]}` : "");
  if (name === "load_skill") return `Loading skill${arg("skill_name")}`;
  if (name === "read_file") return arg("path") ? `Reading${arg("path")}` : "Reading a file";
  if (name === "background_agents_start_task") return `Delegating to${arg("agent_name") || " a specialist"}`;
  return PHRASES[name] || `Using ${name}`;
}

export function parseArgs(text: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(text || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}
