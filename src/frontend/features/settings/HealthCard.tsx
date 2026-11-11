import { useEffect, useState } from "react";
import { Card } from "../../components/ui";
import { api } from "../../lib/api";

export function HealthCard() {
  const [health, setHealth] = useState<any>(null);
  useEffect(() => {
    api("/health").then(setHealth);
  }, []);
  if (!health) return null;
  return (
    <Card title="System health"><ul className="flex flex-wrap gap-3 text-sm">{[["Git", health.git], ["Node.js", health.node], ["npx", health.npx], ["Ruff", health.ruff], ["Model", health.llm], ["Skills", health.skills && health.skills.loaded > 0 && health.skills.problems === 0]].map(([name, ok]) => <li key={name as string} className="flex items-center gap-1.5"><span className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`} />{name} {ok ? "ready" : "missing"}</li>)}</ul>{health.skills && <p className="mt-2 text-xs text-slate-500" data-testid="health-skills">{health.skills.loaded} skills loaded{health.skills.problems ? `, ${health.skills.problems} could not be loaded (see the server log)` : ""}. Tool check on enabled models: {health.tool_checks.passed} passed, {health.tool_checks.failed} failed, {health.tool_checks.not_checked} not checked.</p>}</Card>
  );
}
