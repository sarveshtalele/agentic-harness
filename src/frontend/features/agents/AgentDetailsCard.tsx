import { Badge, Card } from "../../components/ui";

const RISK_MEANING: Record<string, string> = {
  low: "Low: reads and writes text only. It cannot reach code by itself.",
  medium: "Medium: reads the repository's code, or can act on project data in chat.",
  high: "Impact: changes code. Its edits land on a separate branch and need a person's review.",
};

// what contains an agent that changes code, so the badge reads as a description of its job and not a warning
const CHANGE_CONTROLS: [string, string][] = [
  ["No tools in workflows", "It can only return proposed edits as text."],
  ["Guarded edits", "Code refuses path escapes, secrets, overwrites, deletions, out-of-scope files, and edits that break syntax."],
  ["Separate branch", "Your main code is never touched."],
  ["Real tests and a confidence review", "Run before anyone is asked to decide."],
  ["Named human approval", "Nothing is committed without it, and agents cannot approve."],
  ["Disable switch and token limits", "The admin can stop it at once."],
];

export function AgentDetailsCard({ item }: { item: any }) {
  return (
    <Card title="Details" actions={<Badge tone={item.enabled ? "emerald" : "rose"}>{item.enabled ? "enabled" : "disabled"}</Badge>}>
      <table className="w-full text-left text-sm" data-testid="agent-details-table"><tbody className="[&_th]:w-48 [&_th]:py-1.5 [&_th]:pr-3 [&_th]:align-top [&_th]:font-semibold [&_tr]:border-t [&_tr]:border-slate-200 dark:[&_tr]:border-slate-800">
        <tr><th>Purpose</th><td>{item.purpose}</td></tr>
        <tr><th>Risk</th><td>{RISK_MEANING[item.risk]}</td></tr>
        {item.risk === "high" && <tr data-testid="impact-controls"><th>Controls on code changes</th><td><ul className="space-y-1 text-xs">{CHANGE_CONTROLS.map(([name, effect]) => <li key={name}><b>{name}.</b> {effect}</li>)}</ul></td></tr>}
        <tr><th>Status</th><td>{item.enabled ? "Enabled" : "Disabled"}</td></tr>
        <tr><th>Prompt version</th><td className="mono text-xs">{item.prompt_ref}</td></tr>
        <tr><th>Skills</th><td className="mono text-xs" data-testid="agent-skills">{item.skills?.length ? item.skills.join(", ") : "None"}</td></tr>
        <tr><th>Workflow tools</th><td className="mono text-xs">{item.workflow_tools.join(", ") || "None. It works only from the text it is given"}</td></tr>
        <tr><th>Chat tools</th><td className="mono text-xs">{item.in_chat ? item.chat_tools.join(", ") : "Not offered in chat"}</td></tr>
        <tr><th>Can change code</th><td>{item.can_change_code ? "Yes, on a branch, after human review" : "No"}</td></tr>
        <tr><th>Tokens per model call</th><td>{item.token_limit.toLocaleString()}</td></tr>
        <tr><th>Evaluations</th><td>{item.eval ? `${item.eval.passed} of ${item.eval.total} passed` : "Not run"}</td></tr>
        <tr><th>Model calls</th><td>{item.calls}</td></tr>
        <tr><th>Tokens used</th><td>{item.tokens.toLocaleString()}</td></tr>
        <tr><th>Average response</th><td>{item.avg_latency_ms === null || item.avg_latency_ms === undefined ? "No calls yet" : `${item.avg_latency_ms} ms`}</td></tr>
        <tr><th>Errors</th><td>{item.errors}</td></tr>
        <tr><th>Guardrail events</th><td>{item.guardrail_events}</td></tr>
        {item.settings_by && <tr><th>Last changed by</th><td>{item.settings_by_name}{item.settings_reason ? `: ${item.settings_reason}` : ""}</td></tr>}
      </tbody></table>
    </Card>
  );
}
