"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Card } from "../../components/ui";

export function RunDocuments({ projectId, runId }: { projectId: string; runId: string | null }) {
  const [docs, setDocs] = useState<any[]>([]);
  useEffect(() => {
    if (!runId) return setDocs([]);
    const load = () => api(`/projects/${projectId}/documents`).then((items) => setDocs(items.filter((d: any) => d.run_id === runId))).catch(() => {});
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [projectId, runId]);
  if (!docs.length) return null;
  return (
    <Card title={`Documents from this run (${docs.length})`}>
      <ul className="space-y-2" data-testid="current-documents">
        {docs.map((d) => (
          <li key={d.id}>
            <Link href={`/projects/${projectId}/documents/${d.id}`} data-testid="document-card" className="flex items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50 p-2.5 transition hover:border-indigo-500 dark:border-slate-700 dark:bg-slate-900">
              <FileText className="h-5 w-5 shrink-0 text-indigo-500" />
              <span className="min-w-0 flex-1"><b className="block truncate text-sm">{d.title}</b><span className="text-[11px] text-slate-500">{d.kind.replace(/_/g, " ")} · v{d.current_version} · {d.status}</span></span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
