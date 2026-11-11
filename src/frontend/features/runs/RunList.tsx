"use client";

import { useEffect, useState } from "react";
import { api, when } from "../../lib/api";
import { Badge } from "../../components/ui";

export function RunList({ projectId, workflow, activeId, onPick, refreshKey }: { projectId: string; workflow?: string[]; activeId?: string | null; onPick: (id: string) => void; refreshKey?: unknown }) {
  const [runs, setRuns] = useState<any[]>([]);
  useEffect(() => {
    const load = () => api(`/projects/${projectId}/runs`).then((items) => setRuns(Array.isArray(items) ? items.filter((r: any) => !workflow || workflow.includes(r.workflow)) : [])).catch(() => {});
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, refreshKey]);
  if (!runs.length) return null;
  return (
    <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
      {runs.slice(0, 8).map((r) => (
        <li key={r.id}>
          <button onClick={() => onPick(r.id)} className={`flex w-full items-center justify-between gap-2 px-1 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-900 ${activeId === r.id ? "font-semibold" : ""}`}>
            <span className="truncate">{r.workflow} · {when(r.started_at)}</span>
            <Badge>{r.status}</Badge>
          </button>
        </li>
      ))}
    </ul>
  );
}
