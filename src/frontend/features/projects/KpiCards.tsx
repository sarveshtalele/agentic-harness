import { Bug, FileText, FolderGit2, ShieldCheck } from "lucide-react";
import Link from "next/link";

type Props = { repo: any; a: any; project: any; base: string; documents: any[]; approvedGates: number; totalGates: number; gatePercentage: number };

export function KpiCards({ repo, a, project, base, documents, approvedGates, totalGates, gatePercentage }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Repository Codebase Health */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
        <div className="flex items-center justify-between text-slate-500">
          <span className="text-xs font-semibold uppercase tracking-wider">Codebase Health</span>
          <FolderGit2 className="h-4 w-4 text-indigo-500" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-white">
            {a.total_files ?? "—"}
          </span>
          <span className="text-xs text-slate-500 font-medium">total source files</span>
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2 dark:border-slate-800/80">
          <span>Tests: <strong className="text-slate-800 dark:text-slate-200">{a.test_file_count ?? "—"}</strong></span>
          <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
            {repo ? (repo.commit_sha || "HEAD").slice(0, 7) : "greenfield"}
          </span>
        </div>
      </div>

      {/* Card 2: Quality Gates Progress */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
        <div className="flex items-center justify-between text-slate-500">
          <span className="text-xs font-semibold uppercase tracking-wider">Quality Gates</span>
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-white">
            {approvedGates}/{totalGates}
          </span>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
            {gatePercentage}% Approved
          </span>
        </div>
        <div className="mt-2.5 h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-500"
            style={{ width: `${gatePercentage}%` }}
          />
        </div>
      </div>

      {/* Card 3: Defect Inventory */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
        <div className="flex items-center justify-between text-slate-500">
          <span className="text-xs font-semibold uppercase tracking-wider">Defect Inventory</span>
          <Bug className="h-4 w-4 text-rose-500" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-white">
            {project?.findings ?? 0}
          </span>
          <span className="text-xs text-slate-500 font-medium">open findings</span>
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2 dark:border-slate-800/80">
          <span className="text-slate-600 dark:text-slate-400">{repo ? "Findings from the last scan" : "No repository connected"}</span>
          <Link href={`${base}/bugs`} className="text-indigo-600 hover:underline dark:text-indigo-400 font-medium">
            Inspect Bugs →
          </Link>
        </div>
      </div>

      {/* Card 4: Governed Documentation */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
        <div className="flex items-center justify-between text-slate-500">
          <span className="text-xs font-semibold uppercase tracking-wider">Governed Docs</span>
          <FileText className="h-4 w-4 text-blue-500" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-white">
            {documents.length}
          </span>
          <span className="text-xs text-slate-500 font-medium">active specs</span>
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2 dark:border-slate-800/80">
          <span className="text-slate-600 dark:text-slate-400">BRD & Test Strategy</span>
          <Link href={`${base}/documents`} className="text-indigo-600 hover:underline dark:text-indigo-400 font-medium">
            View All →
          </Link>
        </div>
      </div>
    </div>
  );
}
