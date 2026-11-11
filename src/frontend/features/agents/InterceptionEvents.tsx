import { ShieldAlert } from "lucide-react";
import { Badge, Card } from "../../components/ui";
import { when } from "../../lib/api";

export function InterceptionEvents({ item }: { item: any }) {
  return (
    <Card title={`Recent Guardrail Interception Events (${item.events_recent.length})`}>
      {item.events_recent.length > 0 ? (
        <div className="grid gap-2.5 md:grid-cols-2">
          {item.events_recent.map((e: any) => (
            <div
              key={e.id}
              className="rounded-xl border border-amber-200/80 bg-amber-50/30 p-3 text-xs dark:border-amber-900/50 dark:bg-amber-950/20 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-slate-200">
                  <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                  <span>{e.kind.replace(/_/g, " ")}</span>
                </div>
                <Badge tone={e.action === "neutralize" || e.action === "neutralized" ? "amber" : "rose"}>
                  {e.action}
                </Badge>
              </div>

              <div className="rounded-lg bg-slate-900 p-2 font-mono text-[11px] text-amber-200 break-all border border-slate-800">
                {e.detail}
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                <span>Enforcement: Automated Runtime Filter</span>
                <span>{when(e.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500 py-3 text-center">No security guardrail violations detected on this agent.</p>
      )}
    </Card>
  );
}
