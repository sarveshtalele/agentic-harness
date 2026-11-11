"use client";

import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, ErrorNote, Spinner } from "../../components/ui";
import { api, when } from "../../lib/api";
import { Detail, Linked } from "./types";

function Links({ title, items, onOpen }: { title: string; items: Linked[]; onOpen: (id: string) => void }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{title} ({items.length})</p>
      {items.length === 0 ? <p className="text-slate-400">None</p> : (
        <ul className="space-y-1">
          {items.map((l) => (
            <li key={`${l.relation}-${l.id}-${l.detail}`} className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] uppercase text-slate-400">{l.relation.replace("_", " ")}</span>
              <Badge tone="indigo">{l.kind}</Badge>
              <button type="button" className="mono text-indigo-600 underline dark:text-indigo-400" onClick={() => onOpen(l.id)}>{l.qualified_name}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** One capability with what links to it (up) and what it links to (down). */
export function CapDrawer({ id, onOpen, onClose }: { id: string; onOpen: (id: string) => void; onClose: () => void }) {
  const [found, setFound] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Detail>(`/capabilities/${encodeURIComponent(id)}`).then((d) => { setFound(d); setError(""); }).catch((e) => setError(e.message));
  }, [id]);
  const shown = found && found.id === id ? found : null;
  return (
    <aside role="dialog" aria-label="Capability detail" data-testid="capability-drawer"
      className="fixed inset-y-0 right-0 z-40 w-full max-w-md space-y-3 overflow-y-auto border-l border-slate-200 bg-white p-4 text-xs shadow-xl dark:border-slate-800 dark:bg-[#0b1229]">
      <div className="flex items-start justify-between gap-2">
        <b className="mono break-all text-sm">{shown?.qualified_name || id}</b>
        <button type="button" aria-label="Close" onClick={onClose} className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800"><X className="h-4 w-4" /></button>
      </div>
      <ErrorNote message={error} />
      {!shown ? (error ? null : <Spinner />) : (
        <>
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="indigo">{shown.kind}</Badge>
            {shown.risk && <Badge>{shown.risk}</Badge>}
            {shown.needs_approval && <Badge tone="amber">needs approval</Badge>}
            <Badge tone={shown.enabled ? "emerald" : "slate"}>{shown.enabled ? "enabled" : "disabled"}</Badge>
          </div>
          <p className="text-slate-700 dark:text-slate-300">{shown.description || "No description in its source."}</p>
          {shown.when_to_use && <p className="text-slate-500">When to use: {shown.when_to_use}</p>}
          <dl className="grid grid-cols-[6rem_1fr] gap-1 text-slate-500">
            <dt>Source</dt><dd className="mono break-all">{shown.source || "—"}</dd>
            <dt>Plugin</dt><dd>{shown.plugin || "—"}</dd>
            <dt>Profiles</dt><dd>{shown.profiles}</dd>
            <dt>SHA-256</dt><dd className="mono break-all">{shown.sha256}</dd>
            <dt>Updated</dt><dd>{when(shown.updated_at)}</dd>
          </dl>
          <Links title="Linked from (up)" items={shown.up} onOpen={onOpen} />
          <Links title="Links to (down)" items={shown.down} onOpen={onOpen} />
        </>
      )}
    </aside>
  );
}
