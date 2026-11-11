"use client";

import { Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { useAuth } from "../../components/AuthGate";
import { Button, ErrorNote, PageTitle, Spinner } from "../../components/ui";
import { AgentCard } from "../../features/agents/AgentCard";
import { GuardrailEvents } from "../../features/agents/GuardrailEvents";
import { GuardrailMatrix } from "../../features/agents/GuardrailMatrix";
import { api } from "../../lib/api";

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
          <AgentCard key={a.key} a={a} tiles={scores?.cards?.[a.key]?.tiles} />
        ))}
      </div>
      {/* Guardrail Policy & Flag Definitions Matrix */}
      <GuardrailMatrix />

      <GuardrailEvents events={events} />
    </AppShell>
  );
}
