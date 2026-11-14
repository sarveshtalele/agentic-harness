"use client";

import { RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../components/AuthGate";
import { Badge, Button, Empty, ErrorNote, Field, inputClass, Spinner } from "../../components/ui";
import { api, when } from "../../lib/api";
import { duration, Run } from "./lib";

const PAGE = 50;
const STATUSES: [string, string][] = [["", "Any status"], ["ok", "OK"], ["error", "Error"]];

interface Filters { project: string; user: string; agent: string; status: string; from: string; to: string; q: string; requests: boolean }
const NONE: Filters = { project: "", user: "", agent: "", status: "", from: "", to: "", q: "", requests: false };

function query(filters: Filters, offset: number): string {
  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  for (const [key, value] of Object.entries(filters)) {
    if (key === "requests") { if (value) params.set("requests", "true"); }
    else if (value) params.set(key, key === "from" || key === "to" ? new Date(String(value)).toISOString() : String(value));
  }
  return params.toString();
}

/** The runs list: one row per root span, newest first, filtered and paged on the server. */
export function RunsTable({ onOpen }: { onOpen: (traceId: string) => void }) {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const [filters, setFilters] = useState<Filters>(NONE);
  const [draft, setDraft] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ items: Run[]; total: number; scope: string } | null>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const load = useCallback(() => {
    api(`/traces?${query(filters, offset)}`).then((found) => { setData(found); setError(""); }).catch((e) => setError(e.message));
  }, [filters, offset]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { api("/projects").then(setProjects).catch(() => setProjects([])); }, []);
  useEffect(() => { if (admin) api("/users").then(setUsers).catch(() => setUsers([])); }, [admin]);

  const set = (change: Partial<Filters>) => { setOffset(0); setFilters((current) => ({ ...current, ...change })); };
  const select = (key: keyof Filters, label: string, options: [string, string][]) => (
    <Field label={label}>
      <select aria-label={label} className={inputClass} value={String(filters[key])} onChange={(e) => set({ [key]: e.target.value })}>
        {options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
      </select>
    </Field>
  );

  return (
    <div className="space-y-3">
      <p data-testid="trace-scope" className="text-xs font-semibold text-slate-500">{data ? (data.scope === "all" ? "All runs" : "You see your own runs") : ""}</p>
      <Button variant="secondary" className="md:hidden" aria-expanded={showFilters} onClick={() => setShowFilters(!showFilters)}>{showFilters ? "Hide filters" : "Show filters"}</Button>
      <div className={`${showFilters ? "grid" : "hidden"} gap-2 md:grid md:grid-cols-4`}>
        {select("project", "Project", [["", "All projects"], ...projects.map((p): [string, string] => [p.id, p.name])])}
        {admin && select("user", "User", [["", "All users"], ["admin", "Administrator"], ...users.map((u): [string, string] => [u.id, u.username])])}
        <Field label="Agent"><input aria-label="Agent" placeholder="e.g. qe-engineer" className={inputClass} value={filters.agent} onChange={(e) => set({ agent: e.target.value.trim() })} /></Field>
        {select("status", "Status", STATUSES)}
        <Field label="From"><input aria-label="From" type="datetime-local" className={inputClass} value={filters.from} onChange={(e) => set({ from: e.target.value })} /></Field>
        <Field label="To"><input aria-label="To" type="datetime-local" className={inputClass} value={filters.to} onChange={(e) => set({ to: e.target.value })} /></Field>
        <form className="flex items-end gap-2 md:col-span-2" onSubmit={(e) => { e.preventDefault(); set({ q: draft.trim() }); }}>
          <div className="min-w-0 flex-1"><Field label="Search"><input aria-label="Search runs" placeholder="Span names and attributes" className={inputClass} value={draft} onChange={(e) => setDraft(e.target.value)} /></Field></div>
          <Button type="submit" variant="secondary"><Search className="h-4 w-4" /> Search</Button>
        </form>
      </div>
      <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={filters.requests} onChange={(e) => set({ requests: e.target.checked })} /> Include plain API requests
        </label>
        <Button variant="secondary" onClick={load}><RefreshCw className="h-4 w-4" /> Refresh</Button>
      </div>
      <ErrorNote message={error} />
      {!data ? (error ? null : <Spinner />) : data.items.length === 0 ? (
        <Empty title="No traces yet">A chat turn, a workflow run, or a Skill Studio step appears here once it finishes.</Empty>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-xs" data-testid="runs-table">
            <thead className="bg-slate-100 text-slate-600 dark:bg-slate-900 dark:text-slate-400">
              <tr>{["Name", "User", "Project", "Agent", "Model", "Status", "Duration", "Tokens", "Started"].map((h) => <th key={h} className="px-2 py-1.5 font-semibold">{h}</th>)}</tr>
            </thead>
            <tbody>
              {data.items.map((run) => (
                <tr key={run.trace_id} data-testid="run-row" onClick={() => onOpen(run.trace_id)} className="cursor-pointer border-t border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900">
                  <td className="px-2 py-1.5"><button type="button" className="mono text-left text-indigo-600 underline dark:text-indigo-400" onClick={(e) => { e.stopPropagation(); onOpen(run.trace_id); }}>{run.name}</button></td>
                  <td className="px-2 py-1.5">{run.user || run.user_id || "—"}</td>
                  <td className="px-2 py-1.5">{run.project || run.project_id || "—"}</td>
                  <td className="px-2 py-1.5">{run.agent || "—"}</td>
                  <td className="mono px-2 py-1.5">{run.model || "—"}</td>
                  <td className="px-2 py-1.5"><Badge tone={run.status === "error" ? "rose" : "emerald"}>{run.status}</Badge></td>
                  <td className="whitespace-nowrap px-2 py-1.5">{duration(run.duration_ms)}</td>
                  <td className="whitespace-nowrap px-2 py-1.5">{run.tokens_in + run.tokens_out ? `${run.tokens_in} in / ${run.tokens_out} out` : "—"}</td>
                  <td className="whitespace-nowrap px-2 py-1.5 text-slate-500">{when(run.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && data.total > PAGE && (
        <div className="flex items-center justify-end gap-2 text-xs text-slate-500">
          <span>{offset + 1}–{Math.min(offset + PAGE, data.total)} of {data.total}</span>
          <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</Button>
          <Button variant="secondary" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>Next</Button>
        </div>
      )}
    </div>
  );
}
