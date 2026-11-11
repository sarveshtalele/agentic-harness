"use client";

import { Badge } from "../../components/ui";
import { Capability } from "./types";

/** The flat registry: one row per capability the signed-in user may see. */
export function CapTable({ items, onOpen }: { items: Capability[]; onOpen: (id: string) => void }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-left text-xs" data-testid="capabilities-table">
        <thead className="bg-slate-100 text-slate-600 dark:bg-slate-900 dark:text-slate-400">
          <tr>{["Kind", "Name", "Description", "Source", "Risk", "Approval", "Enabled"].map((h) => <th key={h} className="px-2 py-1.5 font-semibold">{h}</th>)}</tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id} data-testid="capability-row" onClick={() => onOpen(c.id)} className="cursor-pointer border-t border-slate-200 align-top hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900">
              <td className="px-2 py-1.5"><Badge tone="indigo">{c.kind}</Badge></td>
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
  );
}
