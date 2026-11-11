"use client";

import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge, Button, Card, ErrorNote, inputClass, Spinner } from "../../components/ui";
import { api, when } from "../../lib/api";
import { buildTree, duration, matches, TraceDetail, visibleRows } from "./lib";
import { SpanDetail } from "./SpanDetail";

/** One run: a collapsible span tree beside a waterfall timeline whose bars are scaled to each span's duration. */
export function RunView({ traceId, onBack }: { traceId: string; onBack: () => void }) {
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [error, setError] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState("");
  const [find, setFind] = useState("");

  useEffect(() => {
    api(`/traces/${encodeURIComponent(traceId)}`).then((found: TraceDetail) => { setTrace(found); setError(""); }).catch((e) => setError(e.message));
  }, [traceId]);

  const tops = useMemo(() => buildTree(trace?.spans || []), [trace]);
  const rows = useMemo(() => visibleRows(tops, collapsed), [tops, collapsed]);
  const bounds = useMemo(() => {
    const spans = trace?.spans || [];
    const start = Math.min(...spans.map((s) => Date.parse(s.started_at)));
    const end = Math.max(...spans.map((s) => Date.parse(s.ended_at)));
    return { start, total: Math.max(end - start, 1) };
  }, [trace]);

  if (error) return <div className="space-y-2"><Button variant="secondary" onClick={onBack}><ArrowLeft className="h-4 w-4" /> All runs</Button><ErrorNote message={error} /></div>;
  if (!trace) return <Spinner />;
  const current = trace.spans.find((s) => s.span_id === selected) || trace.spans.find((s) => !s.parent_id) || trace.spans[0];
  const toggle = (id: string) => setCollapsed((was) => { const next = new Set(was); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const root = trace.root;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="secondary" onClick={onBack}><ArrowLeft className="h-4 w-4" /> All runs</Button>
        <input aria-label="Search in this run" placeholder="Search in this run" className={`${inputClass} max-w-xs`} value={find} onChange={(e) => setFind(e.target.value)} />
      </div>
      <Card title={<span className="mono">{root.name}</span>} actions={<Badge tone={root.status === "error" ? "rose" : "emerald"}>{root.status}</Badge>}>
        <p className="text-xs text-slate-500">
          {when(root.started_at)} · {duration(root.duration_ms)} · {trace.spans.length} spans
          {root.user && ` · ${root.user}`}{root.project && ` · ${root.project}`}{root.agent && ` · ${root.agent}`}{root.model && ` · ${root.model}`}
          {root.tokens_in + root.tokens_out > 0 && ` · ${root.tokens_in} in / ${root.tokens_out} out tokens`}
          {root.error_id && <span className="mono"> · error id {root.error_id}</span>}
        </p>
      </Card>
      <div className="grid gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800" data-testid="span-tree">
          {rows.map((span) => {
            const left = ((Date.parse(span.started_at) - bounds.start) / bounds.total) * 100;
            const width = Math.max((span.duration_ms / bounds.total) * 100, 0.5);
            const hit = matches(span, find);
            return (
              <div key={span.span_id} data-testid="span-row" aria-selected={span.span_id === current?.span_id}
                className={`grid grid-cols-[minmax(12rem,45%)_1fr] items-center gap-2 border-b border-slate-200 px-2 py-1 text-xs last:border-0 dark:border-slate-800 ${span.span_id === current?.span_id ? "bg-indigo-500/10" : ""} ${hit ? "ring-1 ring-inset ring-amber-500" : ""}`}>
                <div className="flex min-w-0 items-center gap-1" style={{ paddingLeft: `${span.depth * 14}px` }}>
                  {span.children.length > 0 ? (
                    <button type="button" aria-label={collapsed.has(span.span_id) ? "Expand" : "Collapse"} aria-expanded={!collapsed.has(span.span_id)} onClick={() => toggle(span.span_id)} className="text-slate-500">
                      {collapsed.has(span.span_id) ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                    </button>
                  ) : <span className="w-3.5" />}
                  <button type="button" onClick={() => setSelected(span.span_id)} className={`mono truncate text-left ${span.status === "error" ? "text-rose-600 dark:text-rose-400" : ""}`} title={span.name}>{span.name}</button>
                </div>
                <button type="button" aria-label={`${span.name} took ${duration(span.duration_ms)}`} onClick={() => setSelected(span.span_id)} className="relative h-4 w-full rounded bg-slate-100 dark:bg-slate-900">
                  <span className={`absolute top-0 h-4 rounded ${span.status === "error" ? "bg-rose-500" : "bg-indigo-500"}`} style={{ left: `${Math.min(left, 99.5)}%`, width: `${Math.min(width, 100 - Math.min(left, 99.5))}%` }} />
                  <span className="absolute right-1 top-0 text-[10px] leading-4 text-slate-500">{duration(span.duration_ms)}</span>
                </button>
              </div>
            );
          })}
        </div>
        <Card>{current ? <SpanDetail span={current} /> : <p className="text-xs text-slate-500">This trace has no spans.</p>}</Card>
      </div>
    </div>
  );
}
