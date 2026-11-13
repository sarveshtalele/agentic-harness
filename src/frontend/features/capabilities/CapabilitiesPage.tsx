"use client";

import { ListTree, RefreshCw, Table } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../components/AuthGate";
import { Button, Empty, ErrorNote, inputClass, Spinner } from "../../components/ui";
import { api, when } from "../../lib/api";
import { CapDrawer } from "./CapDrawer";
import { CapTable } from "./CapTable";
import { CapTree } from "./CapTree";
import { Capability, TreeNode, Version } from "./types";

/** /capabilities: the registry as a table or a tree, filtered by kind and text, with a detail drawer. */
export function CapabilitiesPage() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const [list, setList] = useState<{ version: Version | null; items: Capability[] } | null>(null);
  const [roots, setRoots] = useState<TreeNode[] | null>(null);
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");
  const [tree, setTree] = useState(false);
  const [open, setOpen] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api("/capabilities").then((found) => { setList(found); setError(""); }).catch((e) => setError(e.message));
    api("/capabilities/tree").then((found) => setRoots(found.roots)).catch((e) => setError(e.message));
  }, []);
  useEffect(() => { load(); }, [load]);

  const sync = () => {
    setBusy(true);
    api("/capabilities/sync", { method: "POST" }).then(load).catch((e) => setError(e.message)).finally(() => setBusy(false));
  };
  const kinds = useMemo(() => [...new Set((list?.items || []).map((c) => c.kind))].sort(), [list]);
  const shown = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return (list?.items || []).filter((c) => (!kind || c.kind === kind) && words.every((w) => `${c.qualified_name} ${c.description}`.toLowerCase().includes(w)));
  }, [list, kind, q]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span data-testid="registry-version">
          {list?.version ? `${list.version.capabilities} capabilities, ${list.version.links} links. Synced ${when(list.version.synced_at)}, version ${list.version.hash.slice(0, 12)}` : ""}
          {list ? ` · You see ${list.items.length}${admin ? " (administrator: all)" : ""}` : ""}
        </span>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setTree(!tree)}>{tree ? <><Table className="h-4 w-4" /> Table</> : <><ListTree className="h-4 w-4" /> Tree</>}</Button>
          {admin && <Button variant="secondary" busy={busy} onClick={sync}><RefreshCw className="h-4 w-4" /> Sync now</Button>}
        </div>
      </div>
      <ErrorNote message={error} />
      {list?.version?.problems?.length ? (
        <details className="text-xs text-amber-700 dark:text-amber-400"><summary>{list.version.problems.length} problems in the last sync</summary>
          <ul className="mono list-disc pl-5">{list.version.problems.map((p) => <li key={p}>{p}</li>)}</ul></details>
      ) : null}
      {!list ? (error ? null : <Spinner />) : !list.version ? (
        <Empty title="Registry not synced yet">{admin ? "Press Sync now to read every tool, agent, skill and workflow from the code." : "An administrator syncs it."}</Empty>
      ) : tree ? (
        roots ? <CapTree roots={roots} onOpen={setOpen} /> : <Spinner />
      ) : (
        <>
          <div className="grid gap-2 md:grid-cols-3">
            <select aria-label="Kind" className={inputClass} value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="">All kinds</option>
              {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <input aria-label="Search capabilities" placeholder="Search names and descriptions" className={`${inputClass} md:col-span-2`} value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          {shown.length ? <CapTable items={shown} onOpen={setOpen} expanded={!!(kind || q.trim())} /> : <Empty title="Nothing matches">Change the kind or the search.</Empty>}
        </>
      )}
      {open && <CapDrawer id={open} onOpen={setOpen} onClose={() => setOpen("")} />}
    </div>
  );
}
