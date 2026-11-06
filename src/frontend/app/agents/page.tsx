"use client";

import { Play, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { useAuth } from "../../components/AuthGate";
import { Badge, Button, Card, Empty, ErrorNote, PageTitle, Spinner } from "../../components/ui";
import { Tiles } from "../../components/EvalScores";
import { api, when } from "../../lib/api";

const riskTone: Record<string, string> = { low: "emerald", medium: "amber", high: "rose" };
const riskLabel: Record<string, string> = { low: "low risk", medium: "medium risk", high: "Impact: changes code" };

export default function AgentsPage() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const [agents, setAgents] = useState<any[] | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [scores, setScores] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    api("/agents").then(setAgents).catch((e) => setError(e.message));
    api("/evals/cards").then(setScores).catch(() => setScores(null));
    if (admin) api("/agents/guardrail-events").then(setEvents);
  }, [admin]);
  useEffect(() => {
    load();
  }, [load]);
  const runAll = async () => {
    setRunning(true);
    setError("");
    try {
      await api("/agents/evals/run-all", { method: "POST" });
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };
  if (!agents) return <AppShell><ErrorNote message={error} />{!error && <Spinner />}</AppShell>;
  const evaluated = agents.filter((a) => a.eval);
  const stats = [
    ["Agents", agents.length], ["Enabled", agents.filter((a) => a.enabled).length],
    ["Evaluation cases passed", evaluated.length ? `${evaluated.reduce((n, a) => n + a.eval.passed, 0)}/${evaluated.reduce((n, a) => n + a.eval.total, 0)}` : "Not run"],
    ["Model calls", agents.reduce((n, a) => n + a.calls, 0)], ["Tokens", agents.reduce((n, a) => n + a.tokens, 0).toLocaleString()], ["Guardrail events", agents.reduce((n, a) => n + a.guardrail_events, 0)],
  ];
  return (
    <AppShell>
      <PageTitle title="Agents" subtitle="Policy, evaluations, guardrails, and live usage for every agent. All figures come from recorded calls." actions={admin ? <Button busy={running} onClick={runAll}><Play className="h-4 w-4" /> {running ? "Running evaluations" : "Run all evaluations"}</Button> : undefined} />
      <ErrorNote message={error} />
      <dl className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-6" data-testid="agent-stats">
        {stats.map(([k, v]) => <div key={k as string} className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-[#0b1329]"><dd className="text-lg font-bold">{v}</dd><dt className="text-[11px] text-slate-500">{k}</dt></div>)}
      </dl>
      <p className="mb-3 text-xs text-slate-500" data-testid="risk-legend"><b>Risk</b> shows what an agent could affect, not how it is behaving. <b>Low</b> handles text only. <b>Medium</b> reads code or acts on project data. <b>Impact: changes code</b> marks an agent that can change code, always on a separate branch with a person&apos;s review.</p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="agent-cards">
        {agents.map((a) => (
          <Link key={a.key} href={`/agents/${a.key}`} data-testid="agent-card" className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 transition hover:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]">
            <span className="flex items-center justify-between gap-2"><b className="text-sm">{a.name}</b><Badge tone={riskTone[a.risk]}>{riskLabel[a.risk] ?? `${a.risk} risk`}</Badge></span>
            <span className="mt-1 min-h-8 text-xs text-slate-600 dark:text-slate-400">{a.purpose}</span>
            <span className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px]">
              <Badge tone={a.enabled ? "emerald" : "rose"}>{a.enabled ? "enabled" : "disabled"}</Badge>
              <Badge>{a.prompt_ref.split(":")[0].split("@")[1]}</Badge>
              {a.eval ? <Badge tone={a.eval.passed === a.eval.total ? (a.eval.current ? "emerald" : "amber") : "rose"}>{`evals ${a.eval.passed}/${a.eval.total}${a.eval.current ? "" : " old prompt"}`}</Badge> : <Badge>evals not run</Badge>}
            </span>
            <Tiles tiles={scores?.cards?.[a.key]?.tiles} />
            <span className="mt-2 text-[11px] text-slate-500">{a.calls} calls · {a.tokens.toLocaleString()} tokens · {a.errors} errors</span>
          </Link>
        ))}
      </div>
      <div className="mt-4">
        <Card title={<span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-500" /> Recent Guardrail Events ({events.length})</span>}>
          {events.length ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 max-h-[500px] overflow-y-auto pr-1">
              {events.map((e) => {
                const isInjection = e.kind?.includes("prompt_injection") || e.detail?.includes("Ignore all previous");
                const isSecret = e.kind?.includes("secret") || e.action === "redacted";
                const tone = isInjection ? "rose" : isSecret ? "amber" : "indigo";
                const badgeLabel = e.action ? e.action.toUpperCase() : "INTERCEPTED";

                return (
                  <div
                    key={e.id}
                    className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs transition hover:border-indigo-400 dark:border-slate-800 dark:bg-[#0b1329]"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-1.5">
                        <span className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                          <ShieldAlert className={`h-3.5 w-3.5 ${isInjection ? "text-rose-500" : isSecret ? "text-amber-500" : "text-indigo-500"}`} />
                          <span className="capitalize">{e.kind ? e.kind.replace(/_/g, " ") : "Policy Guardrail"}</span>
                        </span>
                        <Badge tone={tone}>{badgeLabel}</Badge>
                      </div>

                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {e.agent || "runtime-guard"}
                        </span>
                      </div>

                      <div className="rounded-lg border border-slate-100 bg-slate-50 p-2 font-mono text-[11px] text-slate-700 dark:border-slate-800/80 dark:bg-slate-950/70 dark:text-slate-300 overflow-x-auto max-h-24 whitespace-pre-wrap break-all">
                        {e.detail}
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[10px] text-slate-400 dark:border-slate-800/60">
                      <span className="flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                        <span>Zero-Trust Demarcation</span>
                      </span>
                      <span>{when(e.created_at)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <Empty title="No guardrail events recorded" />
          )}
        </Card>
      </div>
    </AppShell>
  );
}
