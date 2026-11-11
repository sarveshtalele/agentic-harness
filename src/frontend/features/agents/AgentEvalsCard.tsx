import { Play } from "lucide-react";
import { Badge, Button, Card } from "../../components/ui";
import { when } from "../../lib/api";

export function AgentEvalsCard({ item, admin, running, evaluate }: { item: any; admin: boolean; running: boolean; evaluate: () => void }) {
  const latest = item.evals[0];
  return (
    <Card title="Evaluations" actions={admin && item.has_evals && <Button variant="secondary" busy={running} disabled={!item.enabled} onClick={evaluate}><Play className="h-4 w-4" /> Run on the real model</Button>}>
      {latest ? (
        <>
          <p className="mb-2 text-xs text-slate-500">Latest on <span className="mono">{latest.prompt_ref}</span>, {when(latest.created_at)}</p>
          <ul className="space-y-1 text-sm">{latest.results.map((r: any) => (
            <li key={r.name}>
              {r.passed === null ? <Badge tone="amber">needs grader</Badge> : <Badge tone={r.passed ? "emerald" : "rose"}>{r.passed ? "pass" : "fail"}</Badge>} <Badge>{r.category}</Badge> {r.skill && <Badge tone="indigo">{`skill ${r.skill}`}</Badge>} {r.name.replace(/_/g, " ")}
              {r.passed === null && <p className="ml-1 text-xs text-slate-500">Not scored: the plugin wrote these expectations for a person or a grader, and no code can check them yet.</p>}
              {!r.passed && <p className="mono ml-1 text-xs text-rose-500">{r.failed_checks.join("; ")}</p>}
            </li>
          ))}</ul>
        </>
      ) : <p className="text-sm text-slate-500">Not evaluated yet.</p>}
    </Card>
  );
}
