"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "../../../components/AppShell";
import { useAuth } from "../../../components/AuthGate";
import { PageTitle, Spinner, useToast } from "../../../components/ui";
import { AgentScores } from "../../../components/EvalScores";
import { ActiveGuardrails } from "../../../features/agents/ActiveGuardrails";
import { AgentCallsCard } from "../../../features/agents/AgentCallsCard";
import { AgentControlsCard } from "../../../features/agents/AgentControlsCard";
import { AgentDetailsCard } from "../../../features/agents/AgentDetailsCard";
import { AgentEvalsCard } from "../../../features/agents/AgentEvalsCard";
import { InterceptionEvents } from "../../../features/agents/InterceptionEvents";
import { api } from "../../../lib/api";

function Detail({ agentKey }: { agentKey: string }) {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const onChange = () => {};
  const [item, setItem] = useState<any>(null);
  const [reason, setReason] = useState("");
  const [limit, setLimit] = useState("");
  const [model, setModel] = useState("");
  const [choices, setChoices] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();
  const load = useCallback(async () => {
    const data = await api(`/agents/${agentKey}`);
    setItem(data);
    setLimit(String(data.token_limit));
    setModel(data.model || "");
  }, [agentKey]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (user?.role === "admin") api("/models").then((all: any[]) => setChoices(all.filter((m) => m.enabled).map((m) => m.name))).catch(() => setChoices([]));
  }, [user?.role]);
  if (!item) return <Spinner />;
  const save = async (enabled: boolean) => {
    setError("");
    try {
      await api(`/agents/${agentKey}/settings`, { method: "PUT", json: { enabled, max_tokens: Number(limit) || null, reason, model } });
      setReason("");
      await load();
      onChange();
      toast("Agent settings saved");
    } catch (e: any) {
      setError(e.message);
    }
  };
  const evaluate = async () => {
    setRunning(true);
    setError("");
    try {
      await api(`/agents/${agentKey}/evals`, { method: "POST" });
      await load();
      onChange();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };
  const latest = item.evals[0];
  return (
    <div className="space-y-4" data-testid="agent-detail">
      <AgentDetailsCard item={item} />
      {admin && <AgentControlsCard item={item} user={user} reason={reason} setReason={setReason} limit={limit} setLimit={setLimit} model={model} setModel={setModel} choices={choices} error={error} save={save} />}
      <AgentEvalsCard item={item} admin={admin} running={running} evaluate={evaluate} />
      <AgentScores agentKey={agentKey} admin={admin} enabled={item.enabled} />
      <AgentCallsCard item={item} />
      {/* Guardrail Policy Architecture Cards */}
      <ActiveGuardrails />
      {/* Recent Guardrail Interceptions as Individual Cards */}
      <InterceptionEvents item={item} />
    </div>
  );
}

export default function AgentPage() {
  const { key } = useParams<{ key: string }>();
  const [name, setName] = useState("");
  useEffect(() => {
    api(`/agents/${key}`).then((item) => setName(item.name)).catch(() => {});
  }, [key]);
  return (
    <AppShell>
      <Link href="/agents" className="mb-2 inline-flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-500"><ArrowLeft className="h-3 w-3" /> Agents</Link>
      <PageTitle title={name || "Agent"} subtitle="Policy, evaluations, and recorded use for this agent." />
      <Detail agentKey={key} />
    </AppShell>
  );
}
