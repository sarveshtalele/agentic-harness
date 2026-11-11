import { FileText } from "lucide-react";
import Link from "next/link";
import { Badge, Card } from "../../components/ui";

export function RecentDocs({ recent, projectId }: { recent: any[]; projectId: string }) {
  const docLink = (d: any) => (
    <li key={d.id} className="flex items-center justify-between gap-2 p-1.5 rounded-lg border border-slate-100 bg-white hover:border-indigo-300 dark:border-slate-800 dark:bg-slate-900/60 transition">
      <div className="flex items-center gap-2 truncate">
        <FileText className="h-3.5 w-3.5 shrink-0 text-indigo-500" />
        <Link className="truncate text-xs font-semibold text-slate-800 hover:text-indigo-600 dark:text-slate-200 dark:hover:text-indigo-400" href={`/projects/${projectId}/documents/${d.id}`}>
          {d.title || "Untitled Document"}
        </Link>
      </div>
      <span className="flex shrink-0 items-center gap-1 text-[10px]">
        <Badge tone="indigo">{d.kind}</Badge>
        <span className="font-mono font-medium text-slate-500">v{d.current_version}</span>
        <Badge tone={d.status === "approved" ? "emerald" : "slate"}>{d.status}</Badge>
      </span>
    </li>
  );

  return (
    <Card
      title="Recent documents"
      actions={
        <Link className="text-xs font-semibold text-indigo-500 hover:underline" href={`/projects/${projectId}/documents`}>
          All documents
        </Link>
      }
    >
      {recent.length ? (
        <ul className="space-y-1.5 text-sm" data-testid="recent-documents">
          {recent.map(docLink)}
        </ul>
      ) : (
        <p className="text-xs text-slate-500">None yet.</p>
      )}
    </Card>
  );
}
