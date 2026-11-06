"use client";

import { HelpCircle, Info, Lock, Play, Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { useAuth } from "../../components/AuthGate";
import { Badge, Button, Card, Empty, ErrorNote, PageTitle, Spinner } from "../../components/ui";
import { Tiles } from "../../components/EvalScores";
import { api, when } from "../../lib/api";

const riskTone: Record<string, string> = { low: "emerald", medium: "amber", high: "rose" };
const riskLabel: Record<string, string> = { low: "low risk", medium: "med risk", high: "changes code" };

interface GuardrailFlagDef {
  key: string;
  name: string;
  severity: "critical" | "high" | "medium" | "low";
  action: "REMOVED" | "REDACTED" | "ENFORCED" | "BLOCKED" | "REFUSED" | "AUTO-HEALED" | "THROTTLED";
  summary: string;
  condition: string;
  mitigation: string;
}

const GUARDRAIL_FLAGS: GuardrailFlagDef[] = [
  {
    key: "prompt_injection",
    name: "Prompt Injection",
    severity: "critical",
    action: "REMOVED",
    summary: "Attempts to hijack the agent system prompt, escape role constraints, or force unvetted outputs.",
    condition: "Input matches known adversarial jailbreak patterns ('Ignore all previous instructions', 'PWNED', role override syntax).",
    mitigation: "Zero-trust token boundary delimiters strip injected instructions before the prompt reaches model context."
  },
  {
    key: "secret",
    name: "Secret Exfiltration",
    severity: "critical",
    action: "REDACTED",
    summary: "Hardcoded credentials, API keys, passwords, or connection strings detected in prompts or outputs.",
    condition: "Entropy scanner or regex detection matches high-entropy strings (e.g. Bearer tokens, AWS/Azure keys, JWTs).",
    mitigation: "Scrubbed with [REDACTED] mask before logging to disk, ledger, or persisting to version history."
  },
  {
    key: "zero_trust",
    name: "Zero-Trust Demarcation",
    severity: "high",
    action: "ENFORCED",
    summary: "Strict sandboxing preventing untrusted repository code from executing within orchestration runtime.",
    condition: "Repository code or test execution invoked during analysis, generation, or verification stages.",
    mitigation: "Subprocess is confined to isolated worktree directory with scrubbed environment variables (clean_env) and non-root execution."
  },
  {
    key: "path_escape",
    name: "Path Traversal / Escape",
    severity: "critical",
    action: "BLOCKED",
    summary: "Attempts to access, write, or unlink files outside the designated project sandbox root.",
    condition: "File path contains directory climbing segments ('..'), symlink escapes, or absolute system paths.",
    mitigation: "safe_path() validates canonical relative resolution within worktree boundary; raises PathEscape if outside."
  },
  {
    key: "tautological_assertion",
    name: "Tautological Assertion",
    severity: "medium",
    action: "REFUSED",
    summary: "Vacuous test assertions that artificially pass without verifying real repository behaviour.",
    condition: "Generated test contains 'assert True', 'expect(true).toBe(true)', or empty test bodies with 'pass'.",
    mitigation: "Static AST checker rejects vacuous asserts and prompts the test-automation-engineer to generate real assertions."
  },
  {
    key: "code_drift",
    name: "AST Symbol Drift / Hallucination",
    severity: "medium",
    action: "AUTO-HEALED",
    summary: "Generated test calls non-existent modules, functions, or hallucinated method signatures.",
    condition: "Static AST analyzer compares test imports and calls against real repository module exports.",
    mitigation: "Sends file back to agent with real ground-truth AST signatures or quarantines failing test cases."
  },
  {
    key: "token_allowance",
    name: "Token Budget Exhaustion",
    severity: "low",
    action: "THROTTLED",
    summary: "Cumulative model token consumption exceeds configured safety limit for the run.",
    condition: "Run token accumulator exceeds ATLAS_RUN_TOKEN_LIMIT threshold.",
    mitigation: "Halts workflow to prevent unexpected API costs; bypassable by Administrator accounts."
  }
];

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
            <Tiles tiles={scores?.cards?.[a.key]?.tiles} />
            <span className="mt-2 text-[11px] text-slate-500">{a.calls} calls · {a.tokens.toLocaleString()} tokens · {a.errors} errors</span>
          </Link>
        ))}
      </div>
      {/* Guardrail Policy & Flag Definitions Matrix */}
      <div className="mt-6">
        <Card
          title={
            <span className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-indigo-500" />
              Guardrail Security Flags & Threat Mitigation Matrix
            </span>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <tr>
                  <th className="pb-2.5 font-semibold">Security Flag</th>
                  <th className="pb-2.5 font-semibold">Severity</th>
                  <th className="pb-2.5 font-semibold">Action Enforced</th>
                  <th className="pb-2.5 font-semibold">Trigger Condition</th>
                  <th className="pb-2.5 font-semibold">Mitigation Strategy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {GUARDRAIL_FLAGS.map((flag) => {
                  const tone =
                    flag.severity === "critical"
                      ? "rose"
                      : flag.severity === "high"
                      ? "amber"
                      : flag.severity === "medium"
                      ? "indigo"
                      : "slate";

                  return (
                    <tr
                      key={flag.key}
                      className="group hover:bg-slate-50/60 dark:hover:bg-slate-900/40 transition-colors"
                    >
                      <td className="py-2.5 pr-3 font-medium text-slate-900 dark:text-slate-100">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold">{flag.name}</span>
                          <div className="relative flex items-center group/tooltip">
                            <Info className="h-3.5 w-3.5 text-slate-400 group-hover/tooltip:text-indigo-600 dark:text-slate-500 dark:group-hover/tooltip:text-indigo-400 cursor-pointer" />
                            {/* Hover Tooltip */}
                            <div className="absolute left-6 bottom-full z-50 hidden group-hover/tooltip:block w-72 rounded-xl border border-slate-200 bg-white p-3 shadow-xl dark:border-slate-800 dark:bg-[#0b1329] dark:text-slate-200 text-[11px] leading-relaxed">
                              <p className="font-bold text-slate-900 dark:text-white mb-1">
                                {flag.name} ({flag.action})
                              </p>
                              <p className="text-slate-600 dark:text-slate-400 mb-2">
                                {flag.summary}
                              </p>
                              <div className="border-t border-slate-100 pt-1.5 dark:border-slate-800 space-y-1">
                                <div>
                                  <span className="font-semibold text-slate-700 dark:text-slate-300">Trigger: </span>
                                  <span className="text-slate-500 dark:text-slate-400">{flag.condition}</span>
                                </div>
                                <div>
                                  <span className="font-semibold text-slate-700 dark:text-slate-300">Defense: </span>
                                  <span className="text-slate-500 dark:text-slate-400">{flag.mitigation}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 pr-3">
                        <Badge tone={tone}>{flag.severity.toUpperCase()}</Badge>
                      </td>
                      <td className="py-2.5 pr-3">
                        <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {flag.action}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-400 max-w-xs">
                        {flag.condition}
                      </td>
                      <td className="py-2.5 text-slate-500 dark:text-slate-400 max-w-sm">
                        {flag.mitigation}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="mt-6">
        <Card title={<span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-500" /> Recent Guardrail Events ({events.length})</span>}>
          {events.length ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 max-h-[580px] overflow-y-auto pr-2">
              {events.map((e) => {
                const isInjection = e.kind?.includes("prompt_injection") || e.detail?.includes("Ignore all previous");
                const isSecret = e.kind?.includes("secret") || e.action === "redacted";
                const tone = isInjection ? "rose" : isSecret ? "amber" : "indigo";
                const badgeLabel = e.action ? e.action.toUpperCase() : "INTERCEPTED";
                const matchedFlag = GUARDRAIL_FLAGS.find((f) =>
                  isInjection
                    ? f.key === "prompt_injection"
                    : isSecret
                    ? f.key === "secret"
                    : f.key === e.kind
                ) || GUARDRAIL_FLAGS[0];

                return (
                  <div
                    key={e.id}
                    className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs transition hover:border-indigo-400 dark:border-slate-800 dark:bg-[#0b1329]"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-1.5">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                          <ShieldAlert className={`h-3.5 w-3.5 ${isInjection ? "text-rose-500" : isSecret ? "text-amber-500" : "text-indigo-500"}`} />
                          <span className="capitalize">{e.kind ? e.kind.replace(/_/g, " ") : "Policy Guardrail"}</span>
                          <div className="relative group/cardtip">
                            <Info className="h-3 w-3 text-slate-400 cursor-pointer hover:text-indigo-600" />
                            <div className="absolute left-4 bottom-full z-50 hidden group-hover/cardtip:block w-64 rounded-xl border border-slate-200 bg-white p-2.5 shadow-xl dark:border-slate-800 dark:bg-[#0b1329] dark:text-slate-200 text-[10px] leading-relaxed">
                              <p className="font-bold text-slate-900 dark:text-white mb-0.5">{matchedFlag.name}</p>
                              <p className="text-slate-600 dark:text-slate-400">{matchedFlag.summary}</p>
                            </div>
                          </div>
                        </div>
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
