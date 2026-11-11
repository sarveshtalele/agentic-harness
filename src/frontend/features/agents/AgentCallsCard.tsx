import { Badge, Card } from "../../components/ui";
import { when } from "../../lib/api";

export function AgentCallsCard({ item }: { item: any }) {
  return (
    <Card title={`Recent model calls (${item.calls_recent.length})`}>
      {item.calls_recent.length ? (
        <div className="max-h-64 overflow-auto"><table className="w-full text-left text-xs"><thead className="text-slate-500"><tr><th className="py-1">When</th><th>Source</th><th>Tokens</th><th>ms</th><th>Tools</th><th>Status</th></tr></thead>
          <tbody>{item.calls_recent.map((c: any) => <tr key={c.id} className="border-t border-slate-200 dark:border-slate-800" title={c.error}><td className="py-1">{when(c.created_at)}</td><td>{c.source}</td><td>{c.tokens_in + c.tokens_out}</td><td>{c.latency_ms}</td><td>{c.tool_calls}</td><td><Badge tone={c.status === "ok" ? "emerald" : "rose"}>{c.status}</Badge></td></tr>)}</tbody></table></div>
      ) : <p className="text-sm text-slate-500">No calls recorded.</p>}
    </Card>
  );
}
