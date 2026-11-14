"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useProject } from "../../../../components/ProjectShell";
import { useAuth } from "../../../../components/AuthGate";
import { Approver } from "../../../../components/Approver";
import { Badge, Button, Card, ErrorNote, Field, inputClass, PageTitle, Spinner } from "../../../../components/ui";
import { api, when } from "../../../../lib/api";
import { actionLabel } from "../../../../lib/labels";

export default function GovernancePage() {
  const { project, gates, refresh } = useProject();
  const [gate, setGate] = useState(0);
  const { user } = useAuth();
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [ledger, setLedger] = useState<any>(null);
  const [pending, setPending] = useState<any[]>([]);
  const load = useCallback(() => {
    api(`/projects/${project.id}/ledger`).then(setLedger).catch(() => setLedger(null));
    api(`/projects/${project.id}/approvals`).then((res) => setPending(Array.isArray(res) ? res : [])).catch(() => setPending([]));
  }, [project.id]);
  useEffect(() => {
    load();
  }, [load]);
  const canSign = (project?.can_sign || []).includes(gate); // the server is the real check
  const decide = async (approved: boolean) => {
    setError("");
    try {
      await api(`/projects/${project.id}/gates/${gate}/decision`, { json: { approved, reason } });
      setReason("");
      refresh();
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };
  if (!ledger) return <Spinner />;
  const check = ledger.verification || {};
  const entries = Array.isArray(ledger.entries) ? ledger.entries : [];
  const safeGates = Array.isArray(gates) ? gates : [];
  const safePending = Array.isArray(pending) ? pending : [];
  return (
    <>
      <PageTitle title="Governance" subtitle="Signed gate decisions and a hash-chained audit ledger." />
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Quality gates">
          <div className="overflow-x-auto"><table className="w-full text-left text-sm">
            <tbody>{safeGates.map((g) => (
              <tr key={g.gate} className="border-t border-slate-200 first:border-0 dark:border-slate-800">
                <td className="py-1.5"><b>G{g.gate} {g.name}</b><br /><span className="text-xs text-slate-500">{g.description}</span></td>
                <td className="text-xs"><Approver item={g} />{g.decided_at && <><br />{when(g.decided_at)}</>}{g.reason && <><br />{g.reason}</>}</td>
                <td><Badge>{g.status}</Badge>{g.signature_valid === false && <Badge tone="rose">bad signature</Badge>}</td>
              </tr>
            ))}</tbody>
          </table></div>
        </Card>
        <Card title={`Awaiting approval (${safePending.length})`}>
          {safePending.length ? <ul className="space-y-2 text-sm">{safePending.map((a) => <li key={a.id}><Link className="font-semibold text-indigo-500 underline" href={`/projects/${project.id}/runs/${a.run_id}`}>{a.title}</Link><p className="text-xs text-slate-500">{a.summary}</p></li>)}</ul> : <p className="text-sm text-slate-500">Nothing is waiting.</p>}
        </Card>
      </div>
      <Card className="mt-4" title="Record a gate decision">
        <p className="mb-2 text-xs text-slate-500">For decisions made outside a run, such as revoking an approval.</p>
        <div className="grid gap-2 md:grid-cols-[160px_1fr_1fr_auto]">
          <Field label="Gate"><select className={inputClass} value={gate} onChange={(e) => setGate(Number(e.target.value))}>{safeGates.map((g) => <option key={g.gate} value={g.gate}>G{g.gate} {g.name}</option>)}</select></Field>
          <Field label="Signing as"><p className="py-2 text-sm font-semibold" data-testid="signing-as">{user?.username}</p></Field>
          <Field label="Reason"><input className={inputClass} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
          <div className="flex items-end gap-2"><Button variant="success" disabled={!canSign} onClick={() => decide(true)}>Approve</Button><Button variant="danger" disabled={!reason.trim() || !canSign} onClick={() => decide(false)}>Reject</Button></div>
        </div>
        <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">Reject needs a reason. Rejecting a gate also clears the approvals of the gates after it.</p>
        {!canSign && <p className="mt-2 text-xs text-slate-500" data-testid="cannot-sign">Your role cannot sign gate G{gate}. Ask the project owner or an administrator.</p>}
        <ErrorNote message={error} />
      </Card>
      <Card className="mt-4" title={<span className="flex items-center gap-2">Audit ledger {check.valid ? <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400" data-testid="ledger-valid"><ShieldCheck className="h-4 w-4" /> Chain valid, {check.entries ?? entries.length} entries</span> : <span className="flex items-center gap-1 text-rose-500"><ShieldAlert className="h-4 w-4" /> Tampering detected at entry {check.broken_at}</span>}</span>}>
        <ul className="max-h-[32rem] space-y-2 overflow-auto sm:hidden" data-testid="ledger-cards">
          {entries.map((e: any) => (
            <li key={e.seq} className="rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-800">
              <p className="flex justify-between gap-2"><b>#{e.seq} {actionLabel(e.action)}</b><span className="text-slate-500">{when(e.ts)}</span></p>
              <p className="mt-0.5">By {e.actor_name}</p>
              <p className="mono break-all text-slate-500" title={e.target}>{e.target}</p>
              <p className="mono text-slate-500" title={e.hash}>{(e.hash || "").slice(0, 10)}</p>
            </li>
          ))}
        </ul>
        <div className="hidden max-h-[32rem] overflow-auto sm:block">
          <table className="w-full min-w-[40rem] text-left text-xs">
            <thead className="sticky top-0 bg-white text-slate-500 dark:bg-[#0b1329]"><tr><th className="px-2 py-1">#</th><th className="px-2">Time</th><th className="px-2">Actor</th><th className="px-2">Action</th><th className="px-2">Target</th><th className="px-2">Hash</th></tr></thead>
            <tbody>{entries.map((e: any) => <tr key={e.seq} className="border-t border-slate-200 dark:border-slate-800"><td className="px-2 py-1">{e.seq}</td><td className="whitespace-nowrap px-2">{when(e.ts)}</td><td className="px-2">{e.actor_name}</td><td className="px-2" title={e.action}>{actionLabel(e.action)}</td><td className="mono max-w-52 truncate px-2" title={e.target}>{e.target}</td><td className="mono px-2 text-slate-500" title={e.hash}>{(e.hash || "").slice(0, 10)}</td></tr>)}</tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
