import Link from "next/link";
import { Badge, Card, Empty } from "../../components/ui";

export function RepoCard({ repo, a, languages, frameworks, base }: { repo: any; a: any; languages: string[]; frameworks: string[]; base: string }) {
  return (
    <Card
      title={
        <Link className="hover:text-indigo-600 transition-colors" href={`${base}/repository`}>
          Repository & Architecture
        </Link>
      }
      actions={
        <Link className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400" href={`${base}/repository`}>
          Manage Repo →
        </Link>
      }
    >
      {repo ? (
        <div className="space-y-3 text-sm">
          <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3 dark:border-slate-800/80 dark:bg-slate-900/50">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="font-semibold uppercase tracking-wider">{repo.kind === "git" ? "Git Remote" : "Uploaded ZIP"}</span>
              <span className="font-mono text-[11px]">Commit: {(repo.commit_sha || "").slice(0, 10)}</span>
            </div>
            <div className="font-mono text-xs text-slate-800 dark:text-slate-200 truncate">
              {repo.url || "Local Sandbox Attached"}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-slate-100 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
              <span className="text-slate-500 block">Total Files</span>
              <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{a.total_files ?? "—"}</span>
            </div>
            <div className="rounded-lg border border-slate-100 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
              <span className="text-slate-500 block">Test Suites</span>
              <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{a.test_file_count ?? "—"}</span>
            </div>
          </div>

          <div>
            <span className="text-xs font-semibold text-slate-500 block mb-1.5">Detected Languages & Frameworks:</span>
            <div className="flex flex-wrap gap-1.5">
              {languages.map((l) => (
                <Badge key={l} tone="indigo">{l}</Badge>
              ))}
              {frameworks.map((f: string) => (
                <Badge key={f}>{f}</Badge>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <Empty title="No repository connected">
          Greenfield projects can start by designing a BRD in BA Studio or importing tests in QE Studio.
        </Empty>
      )}
    </Card>
  );
}
