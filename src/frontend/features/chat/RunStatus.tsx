"use client";

import { Check, Loader2, ShieldQuestion, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "../../components/ui";
import { THINKING, WRITING, parseArgs, toolStatus } from "./status";

export type PendingApproval = { id: string; message?: string; toolCallId?: string; metadata?: any };

type Subscribable = { subscribe: (subscriber: any) => { unsubscribe: () => void } };

/** One live status line per run, from TOOL_CALL_START/END and TEXT_MESSAGE_CONTENT events, plus the lines it went through
 *  and the approval interrupts the run ended with (RUN_FINISHED outcome "interrupt", which MAF sends for risky tools). */
export function useRunStatus(agent: Subscribable) {
  const [status, setStatus] = useState("");
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const trailRef = useRef<string[]>([]);

  const show = useCallback((line: string, replace?: string) => {
    setStatus(line);
    const last = trailRef.current[trailRef.current.length - 1];
    if (replace && last === replace) trailRef.current = [...trailRef.current.slice(0, -1), line];
    else if (last !== line) trailRef.current = [...trailRef.current, line];
  }, []);

  const begin = useCallback(() => {
    trailRef.current = [];
    setApprovals([]);
    show(THINKING);
  }, [show]);

  useEffect(() => {
    const calls: Record<string, { name: string; args: string }> = {};
    const subscription = agent.subscribe({
      onToolCallStartEvent: ({ event }: any) => {
        calls[event.toolCallId] = { name: event.toolCallName, args: "" };
        show(toolStatus(event.toolCallName));
      },
      onToolCallArgsEvent: ({ event }: any) => {
        if (calls[event.toolCallId]) calls[event.toolCallId].args += event.delta;
      },
      onToolCallEndEvent: ({ event }: any) => {
        const call = calls[event.toolCallId];
        if (!call) return;
        const detailed = toolStatus(call.name, parseArgs(call.args));
        if (detailed !== toolStatus(call.name)) show(detailed, toolStatus(call.name));  // only when the arguments add detail
      },
      onTextMessageContentEvent: () => show(WRITING),
      onRunFinishedEvent: (params: any) => setApprovals(params.outcome === "interrupt" ? params.interrupts : []),
    });
    return () => subscription.unsubscribe();
  }, [agent, show]);

  // read through the ref, so the caller gets this run's lines even from a closure made before the run
  return { status, approvals, begin, takeTrail: () => trailRef.current, clearApprovals: () => setApprovals([]) };
}

export function StatusLine({ text }: { text: string }) {
  return <p role="status" data-testid="run-status" className="flex items-center gap-1.5 text-xs text-slate-500"><Loader2 className="h-3 w-3 animate-spin" /> {text || THINKING}</p>;
}

export function StatusTrail({ lines }: { lines?: string[] }) {
  if (!lines?.length) return null;
  return <p data-testid="status-trail" className="mb-1 text-[11px] text-slate-400">{lines.join(" · ")}</p>;
}

/** Approve or Reject each risky tool call the run stopped on; the answer resumes the same run on the server. */
export function ApprovalCards({ approvals, busy, onAnswer }: { approvals: PendingApproval[]; busy: boolean; onAnswer: (id: string, approved: boolean) => void }) {
  return approvals.map((a) => {
    const call = a.metadata?.agent_framework?.function_call || {};
    const name = call.name || "a tool";
    return (
      <div key={a.id} data-testid="approval-card" className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
        <p className="flex items-center gap-1.5 font-semibold"><ShieldQuestion className="h-4 w-4 text-amber-600" /> {a.message || `Approve running ${name}?`}</p>
        {call.arguments && <pre className="mono mt-1 max-h-32 overflow-auto whitespace-pre-wrap text-[11px] text-slate-500">{JSON.stringify(call.arguments, null, 2)}</pre>}
        <div className="mt-2 flex gap-2">
          <Button disabled={busy} onClick={() => onAnswer(a.id, true)} aria-label={`Approve ${name}`}><Check className="h-4 w-4" /> Approve</Button>
          <Button disabled={busy} variant="secondary" onClick={() => onAnswer(a.id, false)} aria-label={`Reject ${name}`}><X className="h-4 w-4" /> Reject</Button>
        </div>
      </div>
    );
  });
}
