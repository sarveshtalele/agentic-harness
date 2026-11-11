"use client";

import { ClipboardCopy, RotateCcw } from "lucide-react";
import { useState } from "react";
import { api } from "../../lib/api";
import { Badge, Button, ErrorNote, useToast } from "../../components/ui";

/** What happened, what to do, and the technical detail collapsed. The failure record is already redacted by the server. */
export function FailureCard({ run, onRetry, busy }: { run: any; onRetry: () => void; busy: boolean }) {
  const toast = useToast();
  const [resumingUnlimited, setResumingUnlimited] = useState(false);
  const f = run.failure;

  const resumeUnlimited = async () => {
    setResumingUnlimited(true);
    try {
      await api(`/runs/${run.id}/resume-unlimited`, { method: "POST" });
      toast("Run resumed with unlimited token allowance");
      onRetry();
    } catch (e: any) {
      toast(e.message || "Failed to resume run", "error");
    } finally {
      setResumingUnlimited(false);
    }
  };

  const isAllowance = f?.code === "AQE-ALLOW-001" || f?.message?.includes("tokens") || (run.error && run.error.includes("tokens"));

  if (!f) {
    return (
      <div className="space-y-2">
        <ErrorNote message={run.status === "interrupted" ? `${run.error}. Retry the failed stage.` : run.error} />
        {isAllowance && (
          <Button variant="primary" busy={resumingUnlimited || busy} onClick={resumeUnlimited} className="bg-emerald-600 hover:bg-emerald-500 text-white">
            <RotateCcw className="mr-1 inline h-3.5 w-3.5" />Resume with Unlimited Tokens
          </Button>
        )}
      </div>
    );
  }

  const diagnostics = () =>
    [`Run ${run.id} (${run.workflow}) ${run.status}`, `Error ${f.id} ${f.code} at stage ${f.stage || "-"}`, f.message, `Action: ${f.action}`,
      `Agent ${f.agent || "-"} attempt ${f.attempt ?? "-"} prompt ${f.prompt_ref || "-"} model ${f.model || "-"} finish ${f.finish_reason || "-"}`,
      `Tokens ${f.tokens_in ?? "-"}/${f.tokens_out ?? "-"} in ${f.duration_ms ?? "-"} ms`,
      f.parse_pos != null ? `Parser position ${f.parse_pos}: ${JSON.stringify(f.parse_context)}` : "",
      f.provider_status ? `Provider status ${f.provider_status} request ${f.provider_request_id || "-"}` : "", f.technical, f.stack].filter(Boolean).join("\n");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(diagnostics());
      toast("Diagnostics copied (secrets are masked)");
    } catch {
      toast("Copy failed. Open the technical detail and copy it by hand.", "error");
    }
  };
  return (
    <div role="alert" className="space-y-2 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm" data-testid="failure-card">
      <div className="flex flex-wrap items-center gap-2"><b>What happened</b> <Badge tone="rose">{f.code}</Badge>{f.stage && <span className="text-xs text-slate-500">in {f.stage}</span>}</div>
      <p>{f.message}</p>
      <p><b>What to do:</b> {f.action}</p>
      <details className="text-xs">
        <summary className="cursor-pointer select-none font-semibold">Technical detail (error {f.id})</summary>
        <pre className="mono mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-[#070d1f] p-2 text-slate-300">{diagnostics()}</pre>
      </details>
      <div className="flex flex-wrap gap-2">
        {isAllowance && (
          <Button variant="primary" busy={resumingUnlimited || busy} onClick={resumeUnlimited} className="bg-emerald-600 hover:bg-emerald-500 text-white">
            <RotateCcw className="mr-1 inline h-3.5 w-3.5" />Resume with Unlimited Tokens
          </Button>
        )}
        <Button variant="primary" busy={busy} onClick={onRetry}><RotateCcw className="mr-1 inline h-3.5 w-3.5" />Retry failed stage</Button>
        <Button variant="secondary" onClick={copy}><ClipboardCopy className="mr-1 inline h-3.5 w-3.5" />Copy diagnostics</Button>
      </div>
    </div>
  );
}
