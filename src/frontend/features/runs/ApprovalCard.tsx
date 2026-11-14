"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useAuth } from "../../components/AuthGate";
import { Badge, Button, ErrorNote, Field, inputClass } from "../../components/ui";
import { BrainstormStep } from "./BrainstormStep";
import { ConfidenceNote } from "./ConfidenceNote";
import { NotExecutedCard } from "./NotExecutedCard";
import { cleanTestName } from "./lib";

export function ApprovalCard({ approval, projectId, onDecided }: { approval: any; projectId: string; onDecided: () => void }) {
  const { user } = useAuth();
  const [feedback, setFeedback] = useState("");
  const [openPr, setOpenPr] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [project, setProject] = useState<any>(null);
  useEffect(() => { api(`/projects/${projectId}`).then(setProject).catch(() => {}); }, [projectId]);
  const payload = approval.payload || {};
  const rejects = (payload.confidence?.records || []).filter((r: any) => r.verdict === "REJECT");
  // The server is the real check; this only hides what it would refuse
  const allowed = !project || (approval.gate === null || approval.gate === undefined ? project.can_write : (project.can_sign || []).includes(approval.gate));
  const decide = async (approved: boolean) => {
    setBusy(true);
    setError("");
    try {
      await api(`/approvals/${approval.id}/decide`, { json: { approved, feedback, open_pr: openPr } });
      onDecided();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  if (["brainstorm_question", "brainstorm_approaches", "builder_check"].includes(payload.kind)) return <BrainstormStep approval={approval} onDecided={onDecided} />;
  return (
    <article className="space-y-3 rounded-xl border border-amber-500/50 bg-amber-500/5 p-4" data-testid="approval-card">
      <div className="flex items-center gap-2">
        <Badge tone="amber">Approval needed</Badge>
        <h3 className="text-sm font-bold">{approval.title}</h3>
      </div>
      <p className="text-sm text-slate-700 dark:text-slate-300">{approval.summary}</p>
      {payload.partial && <div role="alert" className="rounded-lg border border-rose-500/50 bg-rose-500/10 p-2 text-sm" data-testid="partial-result"><b>Partial result, not complete.</b> Missing: {payload.partial.missing.join(", ")}. It cannot be approved. Send it back, or fix the cause ({payload.partial.codes.join(", ")}) and run the stage again.</div>}
      {payload.documents && (
        <ul className="flex flex-wrap gap-2 text-sm">
          {payload.documents.map((doc: string, i: number) => (
            <li key={doc}><Link className="text-indigo-500 underline" target="_blank" href={`/projects/${projectId}/documents/${doc}`}>Open {payload.titles?.[i] || "document"}</Link></li>
          ))}
        </ul>
      )}
      {payload.summary?.verdict === "NOT EXECUTED" && <NotExecutedCard payload={payload} />}
      <ConfidenceNote review={payload.confidence || payload.verification?.confidence} />
      {payload.case_limit && <p className="text-sm" data-testid="case-limit">{payload.case_limit.message}{payload.case_limit.left_out_count ? `: ${payload.case_limit.left_out.join(", ")}` : ""}</p>}
      {payload.estimate && <p className="text-xs text-slate-600 dark:text-slate-400" data-testid="token-estimate">Tokens used so far {payload.estimate.used_so_far}. Next: {payload.estimate.next_step}. {payload.estimate.estimated_tokens === null ? payload.estimate.basis : `Estimate about ${payload.estimate.estimated_tokens} tokens (${payload.estimate.expected_calls} calls at ${payload.estimate.average_tokens_per_call}). ${payload.estimate.basis}.`}</p>}
      {payload.emit_unresolved?.length > 0 && (
        <div role="alert" className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm max-h-64 overflow-y-auto space-y-2" data-testid="emit-unresolved">
          <b className="text-amber-900 dark:text-amber-200 block text-xs uppercase tracking-wider">
            {payload.emit_unresolved.length} tests pending static validation checks:
          </b>
          <div className="space-y-1">
            {payload.emit_unresolved.map((u: any, idx: number) => (
              <div key={idx} className="font-mono text-[11px] text-slate-700 dark:text-slate-300 break-all bg-white/60 dark:bg-slate-900/60 p-2 rounded-lg border border-amber-200/60 dark:border-amber-900/40">
                <span className="font-semibold text-amber-700 dark:text-amber-400">{cleanTestName(u.path)}</span>
                {u.findings?.[0] && <span className="ml-1 text-slate-600 dark:text-slate-400">: {u.findings[0]}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      {payload.execution_summary && <p className="text-sm" data-testid="execution-summary">{payload.execution_summary.text} <span className="text-xs">({payload.execution_summary.source === "agent" ? "written by the qa-execution-engineer and checked against the JUnit counts" : "written by code"})</span></p>}
      {payload.defect_records?.length > 0 && (
        <div className="space-y-2 rounded-xl border border-slate-200 bg-white/80 p-3 shadow-sm dark:border-slate-800 dark:bg-[#070d1f]">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 dark:border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">
              Defect Diagnostics & Root Causes ({payload.defect_records.length} items)
            </span>
            <span className="text-[11px] text-slate-500">Deterministic code classification</span>
          </div>
          <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-100 dark:border-slate-800/80">
            <table className="w-full text-left text-xs table-fixed" data-testid="defect-records">
              <thead className="sticky top-0 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400">
                <tr>
                  <th className="p-2 w-48 font-semibold">Test Case</th>
                  <th className="p-2 w-28 font-semibold">Classification</th>
                  <th className="p-2 min-w-[200px] font-semibold">Root Cause</th>
                  <th className="p-2 min-w-[200px] font-semibold">Recommended Fix</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {payload.defect_records.map((r: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="mono p-2 truncate font-medium text-slate-900 dark:text-slate-100" title={r.test}>
                      {cleanTestName(r.test)}
                    </td>
                    <td className="p-2">
                      <Badge tone={r.classification === "application" ? "rose" : r.classification === "drift" ? "amber" : "slate"}>
                        {r.classification}
                      </Badge>
                    </td>
                    <td className="p-2 break-words text-slate-600 dark:text-slate-300">{r.cause}</td>
                    <td className="p-2 break-words text-slate-600 dark:text-slate-300">{r.fix}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {payload.review && <p className="text-sm">Reviewer score <b>{payload.review.score}</b>: {payload.review.issues?.join("; ") || "no issues"}</p>}
      {payload.verification && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          Test verdict <Badge>{payload.verification.verdict}</Badge>
          {payload.verification.reason && <span className="text-xs">{payload.verification.reason}</span>}
          {payload.verification.suites?.map((s: any) => <span key={s.runner} className="mono text-xs">{s.runner}: {s.passed} passed, {s.failed} failed{s.reason ? ` (${s.reason})` : ""}</span>)}
          {!payload.verification.suites?.length && <span className="text-xs">No registered test runner found in this repository.</span>}
        </div>
      )}
      {payload.verification?.changed_assertions?.length > 0 && (
        <div className="rounded-lg border border-rose-500/50 bg-rose-500/10 p-2 text-sm" data-testid="changed-assertions">
          <b>Existing assertions changed. Check that this is intended:</b>
          <ul className="mono mt-1 text-xs">{payload.verification.changed_assertions.map((line: string, i: number) => <li key={i}>{line}</li>)}</ul>
        </div>
      )}
      {payload.diff !== undefined && <pre className="mono max-h-96 overflow-auto rounded-lg bg-[#070d1f] p-3 text-xs text-slate-200">{payload.diff.split("\n").map((line: string, i: number) => <div key={i} className={line.startsWith("+") ? "text-emerald-400" : line.startsWith("-") ? "text-rose-400" : ""}>{line || " "}</div>)}</pre>}
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Signing as"><p className="py-2 text-sm font-semibold" data-testid="signing-as">{user.username}</p></Field>
        <Field label={rejects.length ? `Reason (required: ${rejects.length} item${rejects.length > 1 ? "s are" : " is"} REJECT, and it is written to the ledger if you approve)` : "Feedback (required to send back)"}><input className={inputClass} data-testid="reject-reason" value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder={rejects.length ? "Why these can be accepted" : "What should change"} /></Field>
      </div>
      {payload.can_open_pr && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={openPr} onChange={(e) => setOpenPr(e.target.checked)} /> Push the branch and open a pull request</label>}
      <ErrorNote message={error} />
      {!allowed && <p className="text-xs text-slate-500" data-testid="cannot-sign">Your role cannot {approval.gate == null ? "approve here" : `sign gate G${approval.gate}`}. Ask the project owner or an administrator.</p>}
      <div className="flex gap-2">
        <Button variant="success" busy={busy} disabled={!!payload.partial || !allowed || (rejects.length > 0 && !feedback.trim())} onClick={() => decide(true)}>Approve</Button>
        <Button variant="danger" busy={busy} disabled={!feedback.trim() || !allowed} onClick={() => decide(false)}>Send back</Button>
      </div>
    </article>
  );
}
