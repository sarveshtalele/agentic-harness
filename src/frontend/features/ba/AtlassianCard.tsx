"use client";

import { Link2, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, ErrorNote, inputClass, useToast } from "../../components/ui";
import { api } from "../../lib/api";

/** Jira and Confluence through the Atlassian remote MCP (R4): shown only when the admin added it and granted it to your
 * role. You connect once with your own Atlassian sign-in, search, tick, and attach; each item becomes a source. */
export function AtlassianCard({ projectId, onAttached }: { projectId: string; onAttached: (ids: string[]) => void }) {
  const [sources, setSources] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Record<string, any[]>>({});
  const [picked, setPicked] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const toast = useToast();
  const load = useCallback(() => api(`/projects/${projectId}/atlassian`).then((r) => setSources(r.sources)).catch(() => setSources([])), [projectId]);
  useEffect(() => { load(); }, [load]);
  if (!sources.length) return null;  // not enabled for you: absent, not greyed

  const base = `/projects/${projectId}/atlassian`;
  const run = async (key: string, work: () => Promise<void>) => {
    setBusy(key); setError("");
    try { await work(); } catch (e: any) { setError(e.message); } finally { setBusy(""); }
  };
  return (
    <Card title={<span className="flex items-center gap-1.5"><Link2 className="h-4 w-4" /> Jira and Confluence</span>}>
      {sources.map((s) => (
        <div key={s.id} className="space-y-2 text-sm" data-testid="outside-source">
          {!s.connected ? (
            <Button busy={busy === `c${s.id}`} onClick={() => run(`c${s.id}`, async () => {
              window.location.href = (await api(`${base}/${s.id}/connect`, { json: { return_to: `/projects/${projectId}/ba` } })).url;
            })}>Connect {s.name}</Button>
          ) : (
            <>
              <div className="flex gap-2">
                <input aria-label={`Search ${s.name}`} className={inputClass} placeholder="Search issues and pages" value={query} onChange={(e) => setQuery(e.target.value)} />
                <Button variant="secondary" aria-label={`Search ${s.name} now`} busy={busy === `s${s.id}`} disabled={query.trim().length < 2} onClick={() => run(`s${s.id}`, async () => {
                  setItems((all) => ({ ...all, [s.id]: [] }));
                  const found = await api(`${base}/${s.id}/search`, { json: { query } });
                  setItems((all) => ({ ...all, [s.id]: found.items }));
                })}><Search className="h-4 w-4" /></Button>
              </div>
              {(items[s.id] || []).map((it) => (
                <label key={it.id} className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={!!picked[`${s.id}:${it.id}`]} onChange={(e) => setPicked((p) => ({ ...p, [`${s.id}:${it.id}`]: e.target.checked }))} />
                  <span className="truncate">{it.title}</span>
                </label>
              ))}
              {items[s.id]?.length === 0 && busy !== `s${s.id}` && query && <p className="text-xs text-slate-500">Nothing found.</p>}
              {(items[s.id] || []).some((it) => picked[`${s.id}:${it.id}`]) && (
                <Button busy={busy === `a${s.id}`} onClick={() => run(`a${s.id}`, async () => {
                  const chosen = (items[s.id] || []).filter((it) => picked[`${s.id}:${it.id}`]);
                  const saved = await api(`${base}/${s.id}/attach`, { json: { items: chosen } });
                  onAttached(saved.sources.map((x: any) => x.id));
                  toast(`Attached ${saved.sources.length} as sources`);
                  setPicked({});
                })}>Attach selected</Button>
              )}
            </>
          )}
        </div>
      ))}
      <ErrorNote message={error} />
    </Card>
  );
}
