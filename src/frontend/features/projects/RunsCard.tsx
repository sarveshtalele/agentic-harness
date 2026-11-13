import Link from "next/link";
import { Badge, Card } from "../../components/ui";
import { when } from "../../lib/api";

export function RunsCard({ recentRuns, base }: { recentRuns: any[]; base: string }) {
  return (
    <Card
      title={
        <Link className="hover:text-indigo-600 transition-colors" href={`${base}/runs`}>
          Runs
        </Link>
      }
      actions={
        <Link className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400" href={`${base}/runs`}>
          Run Observability →
        </Link>
      }
    >
      {recentRuns.length ? (
        <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800/80">
          {recentRuns.map((r: any) => (
            <li key={r.id} className="py-2.5 flex items-center justify-between gap-2">
              <Link className="truncate hover:text-indigo-600 dark:hover:text-indigo-400" href={`${base}/runs/${r.id}`}>
                <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">
                  {r.workflow?.replace("_", " ")}
                </span>
                <span className="text-xs text-slate-500 ml-2">
                  {when(r.started_at)}
                </span>
              </Link>
              <Badge tone={r.status === "completed" ? "emerald" : r.status === "running" ? "indigo" : "slate"}>
                {r.status}
              </Badge>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">No workflow has run yet.</p>
      )}
    </Card>
  );
}
