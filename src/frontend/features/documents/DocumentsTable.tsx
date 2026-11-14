import { Download, Trash2 } from "lucide-react";
import Link from "next/link";
import { Badge, Button, Card } from "../../components/ui";
import { when } from "../../lib/api";
import { getGovernanceId, KIND_LABELS } from "./lib";

type Props = { shown: any[]; project: any; onDownload: (doc: any) => void; onDelete: (doc: any) => void };

export function DocumentsTable({ shown, project, onDownload, onDelete }: Props) {
  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm border-collapse">
          <thead className="border-b border-slate-200 bg-slate-50/80 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:border-slate-800 dark:bg-slate-900/60">
            <tr>
              <th className="w-36 min-w-[130px] px-4 py-3 text-left">Governance ID</th>
              <th className="min-w-[260px] px-4 py-3 text-left">Document Title</th>
              <th className="w-32 min-w-[110px] px-4 py-3 text-left">Spec Kind</th>
              <th className="w-24 min-w-[80px] px-4 py-3 text-left">Version</th>
              <th className="w-32 min-w-[110px] px-4 py-3 text-left">Status</th>
              <th className="w-36 min-w-[140px] px-4 py-3 text-left">Updated</th>
              <th className="w-44 min-w-[160px] px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {shown.map((d, idx) => {
              const govId = getGovernanceId(d, project, idx);
              const displayKind = KIND_LABELS[d.kind] || d.kind.replace(/_/g, " ").toUpperCase();

              return (
                <tr key={d.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/50 transition-colors">
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <span className="inline-flex items-center rounded-md border border-indigo-200 bg-indigo-50/80 px-2.5 py-1 font-mono text-xs font-bold text-indigo-700 dark:border-indigo-800/60 dark:bg-indigo-950/60 dark:text-indigo-300 shadow-sm">
                      {govId}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-medium">
                    <Link
                      className="font-semibold text-slate-900 hover:text-indigo-600 dark:text-slate-100 dark:hover:text-indigo-400 block transition-colors"
                      title={d.title}
                      href={`/projects/${project.id}/documents/${d.id}`}
                    >
                      {d.title || "Untitled Specification"}
                    </Link>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {displayKind}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <span className="inline-flex items-center rounded bg-slate-50 px-2 py-0.5 text-xs font-mono font-semibold text-slate-600 dark:bg-slate-800/60 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700/60">
                      v{d.current_version}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <Badge tone={d.status === "approved" ? "emerald" : "slate"}>
                      {d.status === "approved" ? "Approved" : "Draft"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">
                    {when(d.updated_at)}
                  </td>
                  <td className="px-4 py-3.5 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link href={`/projects/${project.id}/documents/${d.id}`}>
                        <Button variant="secondary" className="!px-2.5 !py-1 !text-xs font-medium">
                          Open Spec
                        </Button>
                      </Link>
                      <Button
                        variant="secondary"
                        className="!p-1 text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400"
                        title="Download Markdown"
                        onClick={() => onDownload(d)}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="danger"
                        className="!p-1 text-rose-500 hover:bg-rose-500/20"
                        title="Delete Document"
                        onClick={() => onDelete(d)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
