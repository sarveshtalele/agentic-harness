import Link from "next/link";
import { Badge, Card, Empty } from "../../components/ui";
import { getGovernanceId } from "../documents/lib";

export function DocumentsCard({ documents, project, base }: { documents: any[]; project: any; base: string }) {
  return (
    <Card
      title={
        <Link className="hover:text-indigo-600 transition-colors" href={`${base}/documents`}>
          Governed Documents & Specs
        </Link>
      }
      actions={
        <Link className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400" href={`${base}/documents`}>
          All Documents ({documents.length}) →
        </Link>
      }
    >
      {documents.length ? (
        <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800/80">
          {documents.map((d: any, idx: number) => {
            const govId = getGovernanceId(d, project, idx);
            return (
              <li key={d.id} className="py-2.5 flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[10px] font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-1.5 py-0.5 rounded">
                      {govId}
                    </span>
                    <Link title={d.title} className="truncate font-semibold text-slate-800 hover:text-indigo-600 dark:text-slate-200 dark:hover:text-indigo-400" href={`${base}/documents/${d.id}`}>
                      {d.title}
                    </Link>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                    <span>Kind: <strong className="text-slate-700 dark:text-slate-300">{d.kind}</strong></span>
                    <span>·</span>
                    <span>v{d.current_version}</span>
                  </div>
                </div>
                <Badge tone={d.status === "approved" ? "emerald" : "slate"}>
                  {d.status}
                </Badge>
              </li>
            );
          })}
        </ul>
      ) : (
        <Empty title="No documents yet">Documents appear here as the stages produce them.</Empty>
      )}
    </Card>
  );
}
