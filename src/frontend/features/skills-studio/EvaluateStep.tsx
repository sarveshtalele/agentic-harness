import { useState } from "react";
import { Badge, Button, Card } from "../../components/ui";
import { api } from "../../lib/api";
import { PlanRecord } from "./types";
import { CallStatus, useCall } from "./useCall";

type Graded = { kind: string; value: string; passed: boolean };
type Side = { output: string; assertions: Graded[] };
type Result = { metrics: Record<string, number | undefined>; n: number; judge_model: string; prompt_ref: string; tokens: number; cases: { case: number; input: string; with_skill: Side; without_skill: Side }[] };
const names: [string, string][] = [["assertion_pass_rate_with_skill", "Pass rate with the skill"], ["assertion_pass_rate_without_skill", "Pass rate without the skill"], ["skill_uplift", "Uplift"]];

function Assertions({ title, side }: { title: string; side: Side }) {
  return (
    <div className="space-y-1"><p className="text-xs font-semibold">{title}</p>
      {side.assertions.map((a, i) => <p key={i} className="flex items-center gap-2 text-xs"><Badge tone={a.passed ? "emerald" : "rose"}>{a.passed ? "passed" : "failed"}</Badge><span className="mono">{a.kind} {a.value}</span></p>)}
    </div>
  );
}

export function EvaluateStep({ record }: { record: PlanRecord }) {
  const [result, setResult] = useState<Result | null>(null);
  const call = useCall();
  const evaluate = () => call.run("Evaluating on the model…", async () => setResult(await api(`/skill-studio/plans/${record.id}/evaluate`, { method: "POST" })));
  return (
    <Card title="7. Evaluate on the model">
      <div className="space-y-3">
        <Button onClick={evaluate} disabled={!!call.busy} busy={!!call.busy} data-testid="studio-evaluate">Run evaluation on the model</Button>
        <CallStatus call={call} />
        {result && (
          <>
            <div className="grid gap-2 sm:grid-cols-3" data-testid="studio-eval-metrics">
              {names.map(([key, label]) => {
                const v = result.metrics[key];
                return <div key={key} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800" data-testid={`studio-metric-${key}`}><p className="text-xs text-slate-500">{label}</p>
                  <p className="text-lg font-bold">{typeof v === "number" ? v.toFixed(2) : "not measured"}</p>
                  <p className="text-[11px] text-slate-500">n={result.n}, judge {result.judge_model}</p></div>;
              })}
            </div>
            <p className="text-xs text-slate-500">Tokens used: {result.tokens}. Prompt <span className="mono">{result.prompt_ref}</span>.</p>
            {result.cases.map((c) => (
              <div key={c.case} className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800" data-testid={`studio-eval-result-${c.case}`}>
                <p className="text-xs"><span className="font-semibold">Case {c.case} input:</span> {c.input}</p>
                <div className="grid gap-3 sm:grid-cols-2"><Assertions title="With the skill" side={c.with_skill} /><Assertions title="Without the skill" side={c.without_skill} /></div>
              </div>
            ))}
          </>
        )}
      </div>
    </Card>
  );
}
