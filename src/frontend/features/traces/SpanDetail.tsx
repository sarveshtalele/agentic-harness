"use client";

import { Badge } from "../../components/ui";
import { duration, errorOf, Span, tokensOf } from "./lib";

const INPUTS = ["input", "gen_ai.tool.call.arguments", "gen_ai.input.messages"];
const OUTPUTS = ["output", "gen_ai.tool.call.result", "gen_ai.output.messages"];

function Block({ title, value }: { title: string; value: unknown }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{title}</p>
      <pre className="mono max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-[#070d1f] p-2 text-[11px] text-slate-200">{text}</pre>
    </div>
  );
}

/** One span: what it took in and gave out (redacted on the server), tokens, duration, and any error with its error id. */
export function SpanDetail({ span }: { span: Span }) {
  const a = span.attributes;
  const tokens = tokensOf(span);
  const error = errorOf(span);
  const errorId = a.error_id ? String(a.error_id) : "";
  const input = INPUTS.find((key) => a[key] !== undefined);
  const output = OUTPUTS.find((key) => a[key] !== undefined);
  return (
    <div className="space-y-3 text-xs" data-testid="span-detail">
      <div className="flex flex-wrap items-center gap-2">
        <b className="mono text-sm">{span.name}</b>
        <Badge tone={span.status === "error" ? "rose" : "emerald"}>{span.status}</Badge>
        <span className="text-slate-500">{span.kind}</span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-slate-500">Duration</dt><dd>{duration(span.duration_ms)}</dd>
        <dt className="text-slate-500">Tokens</dt><dd>{tokens.input + tokens.output ? `${tokens.input} in / ${tokens.output} out` : "—"}</dd>
        <dt className="text-slate-500">Span id</dt><dd className="mono">{span.span_id}</dd>
        {a.tool_call_id !== undefined && (<><dt className="text-slate-500">Tool call row</dt><dd className="mono">{String(a.tool_call_id)}</dd></>)}
      </dl>
      {(error || errorId) && (
        <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-2 text-rose-700 dark:text-rose-300">
          {error || "Failed"}{errorId && <span className="mono"> · error id {errorId}</span>}
        </div>
      )}
      {input && <Block title="Input" value={a[input]} />}
      {output && <Block title="Output" value={a[output]} />}
      <Block title="Attributes" value={a} />
    </div>
  );
}
