import Link from "next/link";
import { Badge } from "../../components/ui";
import { Tiles } from "../../components/EvalScores";

const riskTone: Record<string, string> = { low: "emerald", medium: "amber", high: "rose" };
const riskLabel: Record<string, string> = { low: "low risk", medium: "med risk", high: "changes code" };

export function AgentCard({ a, tiles }: { a: any; tiles: any }) {
  return (
    <Link key={a.key} href={`/agents/${a.key}`} data-testid="agent-card" className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 transition hover:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]">
      <span className="flex items-start justify-between gap-2">
        <b className="text-sm font-bold text-slate-900 dark:text-white leading-tight">{a.name}</b>
        <span className="shrink-0"><Badge tone={riskTone[a.risk]}>{riskLabel[a.risk] ?? `${a.risk} risk`}</Badge></span>
      </span>
      <span className="mt-1 min-h-8 text-xs text-slate-600 dark:text-slate-400">{a.purpose}</span>
      <span className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px]">
        <Badge tone={a.enabled ? "emerald" : "rose"}>{a.enabled ? "enabled" : "disabled"}</Badge>
        <Badge>{a.prompt_ref.split(":")[0].split("@")[1]}</Badge>
        {a.eval ? <Badge tone={a.eval.passed === a.eval.total ? (a.eval.current ? "emerald" : "amber") : "rose"}>{`evals ${a.eval.passed}/${a.eval.total}${a.eval.current ? "" : " old prompt"}`}</Badge> : <Badge>evals not run</Badge>}
      </span>
      <Tiles tiles={tiles} />
      <span className="mt-2 text-[11px] text-slate-500">{a.calls} calls · {a.tokens.toLocaleString()} tokens · {a.errors} errors</span>
    </Link>
  );
}
