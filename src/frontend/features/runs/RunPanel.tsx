"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Approver } from "../../components/Approver";
import { api } from "../../lib/api";
import { Badge, Button, Card, ConfirmModal, useToast } from "../../components/ui";
import { ApprovalCard } from "./ApprovalCard";
import { FailureCard } from "./FailureCard";
import { LiveLog } from "./LiveLog";
import { buildStages, duration } from "./lib";
import { useRunStream } from "./useRunStream";

export function RunPanel({ runId, projectId, onFinished }: { runId: string; projectId: string; onFinished?: () => void }) {
  const { run, events, now, load, follow } = useRunStream(runId, onFinished);
  const toast = useToast();
  const decided = async () => {
    toast("Decision recorded");
    await follow();
  };
  const [retrying, setRetrying] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    variant?: "danger" | "primary";
    onConfirm: () => Promise<void>;
  } | null>(null);
  const retry = async () => {
    setRetrying(true);
    try {
      await api(`/runs/${runId}/retry`, { method: "POST" });
      toast("Retrying from the failed stage");
      await follow();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setRetrying(false);
    }
  };

  if (!run) return null;
  const open = (Array.isArray(run.approvals) ? run.approvals : []).filter((a: any) => a?.status === "pending");
  const cancel = () => {
    setConfirmDialog({
      open: true,
      title: "Stop Autonomous Run?",
      message: "Are you sure you want to stop and cancel this run?",
      confirmLabel: "Stop Run",
      variant: "danger",
      onConfirm: async () => {
        try {
          await api(`/runs/${runId}/cancel`, { method: "POST" });
          await load();
          toast("Run cancelled");
        } catch (e: any) {
          toast(e.message, "error");
        }
      },
    });
  };
  const stages = buildStages(events, run.status);
  const toolCalls = events.filter((e) => e.type === "tool").length;
  const agentCalls = events.filter((e) => e.type === "agent").length;
  const live = run.status === "running";
  const state = run.state || {};
  return (
    <Card
      title={<span className="flex flex-wrap items-center gap-2">Run <span className="mono text-xs font-normal">{(run.id || "").slice(-8)}</span> <Badge>{run.workflow}</Badge> <span data-testid="run-status"><Badge>{run.status}</Badge></span>{live && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}</span>}
      actions={(live || run.status === "waiting_approval") ? <Button variant="danger" className="!px-2 !py-1 !text-xs" onClick={cancel}>Stop run</Button> : undefined}
    >
      <div className="space-y-3">
        <dl className="grid grid-cols-2 gap-2 text-center md:grid-cols-4" data-testid="run-metrics">
          {[["Elapsed", duration(run.started_at, run.ended_at, now)], ["Tokens", ((run.tokens_in || 0) + (run.tokens_out || 0)).toLocaleString()], ["Agent calls", agentCalls], ["Tool calls", toolCalls]].map(([k, v]) => (
            <div key={k as string} className="rounded-lg bg-slate-100 py-1.5 dark:bg-slate-900"><dd className="text-sm font-bold">{v}</dd><dt className="text-[11px] text-slate-500">{k}</dt></div>
          ))}
        </dl>
        {stages.length > 0 && (
          <ol className="flex flex-wrap gap-1.5" data-testid="run-stages" aria-label="Stages">
            {stages.map((stage) => (
              <li key={stage.id} className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-semibold ${stage.status === "running" ? "border-indigo-500 bg-indigo-500/10 text-indigo-600 dark:text-indigo-300" : stage.status === "failed" ? "border-rose-500 text-rose-500" : stage.status === "waiting" ? "border-amber-500 text-amber-600 dark:text-amber-400" : "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"}`}>
                {stage.status === "running" ? <Loader2 className="h-3 w-3 animate-spin" /> : stage.status === "failed" ? <XCircle className="h-3 w-3" /> : stage.status === "waiting" ? <Circle className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
                {stage.label}
              </li>
            ))}
          </ol>
        )}
        <Link className="text-xs text-indigo-500 underline" href={`/projects/${projectId}/observability?run=${runId}`}>Open full trace</Link>
        {(run.status === "failed" || run.status === "interrupted") && <FailureCard run={run} onRetry={retry} busy={retrying} />}
        {(state.branch || state.pull_request) && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            {state.branch && <span>Branch <span className="mono text-xs">{state.branch}</span></span>}
            {state.commit && <span>Commit <span className="mono text-xs">{(state.commit || "").slice(0, 10)}</span></span>}
            {state.worktree && <a className="text-indigo-500 underline" href={`/api/runs/${run.id}/changes.zip`}>Download changed files</a>}
            {state.patch_doc && <a className="text-indigo-500 underline" href={`/api/documents/${state.patch_doc}/export/patch`}>Download patch</a>}
            {state.pull_request && <a className="text-indigo-500 underline" target="_blank" rel="noreferrer" href={state.pull_request.url}>Pull request #{state.pull_request.number}</a>}
            {state.pull_request && <Button variant="secondary" className="!px-2 !py-1 !text-xs" onClick={() => {
              setConfirmDialog({
                open: true,
                title: "Squash-Merge Pull Request?",
                message: "Squash-merge this pull request on GitHub into the repository branch?",
                confirmLabel: "Merge Pull Request",
                variant: "primary",
                onConfirm: async () => {
                  try {
                    await api(`/runs/${run.id}/merge-pr`, { method: "POST" });
                    toast("Pull request merged");
                    await load();
                  } catch (e: any) {
                    toast(e.message, "error");
                  }
                },
              });
            }}>Merge</Button>}
          </div>
        )}
        {state.source_files !== undefined && <p className="text-sm" data-testid="scan-coverage">Reviewed <b>{state.reviewed_files?.length || 0}</b> of <b>{state.source_files}</b> source files{state.unreviewed_files?.length ? `. Not reviewed: ${state.unreviewed_files.join(", ")}` : ""}</p>}
        {state.summary?.verdict && <p className="text-sm">Result <Badge>{state.summary.verdict}</Badge> {state.summary.passed}/{state.summary.executed} tests passed, {state.summary.coverage}% requirement coverage</p>}
        {open.map((a: any) => <ApprovalCard key={a.id} approval={a} projectId={projectId} onDecided={decided} />)}
        <LiveLog events={events} live={live} />
        <div className="max-h-[28rem] space-y-1 overflow-y-auto text-xs" data-testid="run-events">
          {stages.map((stage) => (
            <details key={stage.id} open={stage.status === "running" || stage.status === "failed"} className="rounded-lg border border-slate-200 dark:border-slate-800">
              <summary className="cursor-pointer select-none px-2 py-1.5 font-semibold">{stage.label} <span className="font-normal text-slate-500">{stage.agents ? `· ${stage.agents} agent ${stage.agents === 1 ? "call" : "calls"} · ${stage.tokens.toLocaleString()} tokens` : ""}{stage.tools ? ` · ${stage.tools} tool ${stage.tools === 1 ? "call" : "calls"}` : ""}</span></summary>
              <ol className="space-y-0.5 px-2 pb-2">
                {stage.events.map((e: any) => (
                  <li key={e.seq} className="flex gap-1.5">
                    <span className={`${e.type === "tool" ? "mono text-slate-500" : e.type === "error" ? "text-rose-500" : "text-slate-700 dark:text-slate-300"} min-w-0 break-words`}>
                      {e.type === "approved" && e.decided_by_name ? <Approver item={e} prefix="Approved by " /> : e.message}
                      {e.data?.document_id && <> · <Link className="text-indigo-500 underline" href={`/projects/${projectId}/documents/${e.data.document_id}`}>open</Link></>}
                    </span>
                  </li>
                ))}
              </ol>
            </details>
          ))}
        </div>
      </div>

      {confirmDialog && (
        <ConfirmModal
          open={confirmDialog.open}
          title={confirmDialog.title}
          message={confirmDialog.message}
          confirmLabel={confirmDialog.confirmLabel}
          variant={confirmDialog.variant}
          onConfirm={async () => {
            await confirmDialog.onConfirm();
            setConfirmDialog(null);
          }}
          onCancel={() => setConfirmDialog(null)}
        />
      )}
    </Card>
  );
}
