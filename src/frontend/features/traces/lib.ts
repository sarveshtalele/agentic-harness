/** Trace explorer types and helpers. Every value shown comes from GET /api/traces; attributes are redacted on the server. */

export interface Run {
  trace_id: string;
  name: string;
  status: string;
  duration_ms: number;
  started_at: string;
  project_id: string | null;
  project: string;
  user_id: string | null;
  user: string;
  agent: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  error_id: string;
  spans: number;
}

export interface Span {
  span_id: string;
  parent_id: string | null;
  name: string;
  kind: string;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  status: string;
  attributes: Record<string, unknown>;
}

export interface SpanNode extends Span {
  children: SpanNode[];
  depth: number;
}

export interface TraceDetail {
  trace_id: string;
  root: Run;
  spans: Span[];
}

/** Spans whose parent is not in this trace become top-level nodes, so nothing is lost if a parent was never stored. */
export function buildTree(spans: Span[]): SpanNode[] {
  const nodes = new Map<string, SpanNode>(spans.map((s) => [s.span_id, { ...s, children: [], depth: 0 }]));
  const tops: SpanNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.parent_id ? nodes.get(node.parent_id) : undefined;
    if (parent) parent.children.push(node);
    else tops.push(node);
  }
  const setDepth = (node: SpanNode, depth: number) => {
    node.depth = depth;
    node.children.sort((a, b) => a.started_at.localeCompare(b.started_at));
    node.children.forEach((child) => setDepth(child, depth + 1));
  };
  tops.forEach((top) => setDepth(top, 0));
  return tops;
}

/** The rows to draw: depth first, skipping the children of collapsed spans. */
export function visibleRows(tops: SpanNode[], collapsed: Set<string>): SpanNode[] {
  const out: SpanNode[] = [];
  const walk = (node: SpanNode) => {
    out.push(node);
    if (!collapsed.has(node.span_id)) node.children.forEach(walk);
  };
  tops.forEach(walk);
  return out;
}

export function duration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return ms < 60_000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.floor(ms / 60_000)} min ${Math.round((ms % 60_000) / 1000)} s`;
}

function num(value: unknown): number {
  return typeof value === "number" ? value : Number(value) || 0;
}

/** Our own attributes first, then the OpenTelemetry GenAI names MAF uses. */
export function tokensOf(span: Span): { input: number; output: number } {
  const a = span.attributes;
  return { input: num(a.tokens_in ?? a["gen_ai.usage.input_tokens"]), output: num(a.tokens_out ?? a["gen_ai.usage.output_tokens"]) };
}

export function errorOf(span: Span): string {
  const a = span.attributes;
  return String(a.error ?? a["exception.message"] ?? a.error_type ?? a["error.type"] ?? "");
}

export function matches(span: Span, text: string): boolean {
  if (!text) return false;
  const needle = text.toLowerCase();
  return span.name.toLowerCase().includes(needle) || JSON.stringify(span.attributes).toLowerCase().includes(needle);
}
