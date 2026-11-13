"use client";

import { Badge } from "../../components/ui";
import { Capability } from "./types";

const HEAD = ["Name", "Description", "Source", "Risk", "Approval", "Enabled"];

/** The registry grouped by kind, each group with its count and folded until opened (UI audit U9). A search or a chosen kind
 * opens the groups that match, so a hit is never hidden. */
export function CapTable({ items, onOpen, expanded = false }: { items: Capability[]; onOpen: (id: string) => void; expanded?: boolean }) {
  const groups = new Map<string, Capability[]>();
  for (const c of items) groups.set(c.kind, [...(groups.get(c.kind) || []), c]);
  return (
    <div className="space-y-2" data-testid="capabilities-table">
      {[...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([kind, rows]) => (
        <details key={`${kind}-${expanded}`} open={expanded} className="rounded-lg border border-slate-200 dark:border-slate-800" data-testid="capability-group">
          <summary className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm font-semibold">
            <Badge tone="indigo">{kind}</Badge> <span className="text-slate-500">{rows.length}</span>
          </summary>
          <div className="overflow-x-auto border-t border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-600 dark:bg-slate-900 dark:text-slate-400">
                <tr>{HEAD.map((h) => <th key={h} className="px-2 py-1.5 font-semibold">{h}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} data-testid="capability-row" onClick={() => onOpen(c.id)} className="cursor-pointer border-t border-slate-200 align-top hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900">
                    <td className="mono px-2 py-1.5 text-indigo-600 dark:text-indigo-400">{c.qualified_name}</td>
                    <td className="max-w-md px-2 py-1.5 text-slate-600 dark:text-slate-300">{c.description || "—"}</td>
                    <td className="mono max-w-[16rem] truncate px-2 py-1.5 text-slate-500" title={c.source}>{c.source || "—"}</td>
                    <td className="px-2 py-1.5">{c.risk ? <Badge>{c.risk}</Badge> : "—"}</td>
                    <td className="px-2 py-1.5">{c.needs_approval ? <Badge tone="amber">needs approval</Badge> : "—"}</td>
                    <td className="px-2 py-1.5">{c.enabled ? <Badge tone="emerald">yes</Badge> : <Badge tone="slate">no</Badge>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ))}
    </div>
  );
}
