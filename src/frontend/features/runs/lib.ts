export const verdictTone = (v: string) => (v === "APPROVED" ? "emerald" : v === "REVISE" ? "amber" : v === "REJECT" ? "rose" : "slate");

export function cleanTestName(name: string): string {
  if (!name) return "";
  let clean = name;
  if (clean.includes("tests.agentic_qe.")) {
    clean = clean.split("tests.agentic_qe.").pop() || clean;
  } else if (clean.includes("tests/agentic_qe/")) {
    clean = clean.split("tests/agentic_qe/").pop() || clean;
  } else if (clean.includes("worktrees")) {
    const parts = clean.split(".");
    clean = parts[parts.length - 1] || clean;
  }
  clean = clean.replace(/^[.:/]+/, "");
  return clean;
}

export function duration(start: string, end: string | null, now: number): string {
  const seconds = Math.max(0, Math.round(((end ? new Date(end).getTime() : now) - new Date(start).getTime()) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export function buildStages(events: any[], status: string) {
  const stages: any[] = [];
  const find = (id: string) => stages.find((s) => s.id === id);
  for (const e of events) {
    if (!e.stage) continue;
    let stage = find(e.stage);
    if (!stage) {
      stage = { id: e.stage, label: e.stage.replace(/_/g, " "), status: "done", events: [], tools: 0, agents: 0, tokens: 0 };
      stages.push(stage);
    }
    if (e.type === "stage_start") {
      stage.label = e.message.replace(/^Started /, "");
      stage.status = "running";
    } else if (e.type === "stage_end") stage.status = "done";
    else if (e.type === "approval_required") stage.status = "waiting";
    else if (e.type === "approved") stage.status = "done";
    else if (e.type === "error") stage.status = "failed";
    if (e.type === "tool") stage.tools += 1;
    if (e.type === "agent") {
      stage.agents += 1;
      stage.tokens += e.data?.tokens || 0;
    }
    if (!["stage_start", "stage_end"].includes(e.type)) stage.events.push(e);
  }
  if (status !== "running" && status !== "waiting_approval") for (const stage of stages) if (stage.status === "running") stage.status = status === "failed" ? "failed" : "done";
  return stages;
}
