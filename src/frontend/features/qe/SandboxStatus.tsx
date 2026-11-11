import { AlertTriangle, FolderGit2, GitBranch } from "lucide-react";
import { Badge } from "../../components/ui";

export function SandboxStatus({ project, runId, activeRun }: { project: any; runId: string; activeRun: any }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-[#0b1329]">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
            <FolderGit2 className="h-3.5 w-3.5" />
          </span>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Isolated Repository Sandbox & Worktree Status
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={activeRun?.status === "completed" ? "emerald" : activeRun?.status === "failed" ? "rose" : activeRun?.status === "waiting_approval" ? "amber" : "indigo"}>
            {activeRun?.status ? activeRun.status.replace("_", " ") : "active"}
          </Badge>
          {activeRun?.stage && (
            <span className="font-mono text-xs text-slate-500">
              stage: <b className="text-slate-800 dark:text-slate-200">{activeRun.stage}</b>
            </span>
          )}
        </div>
      </div>

      {activeRun?.status === "waiting_approval" && (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-200 animate-pulse">
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>
              <b>Quality Gate Approval Required:</b> Pipeline execution is currently paused awaiting human review. Review the verification evidence below and select <b>Approve</b> to advance.
            </span>
          </div>
        </div>
      )}

      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Grounded Git Source</span>
          <div className="mt-1 font-mono text-[11px] text-slate-800 dark:text-slate-200 truncate" title={project.git_url || "Local Workspace"}>
            {project.git_url || "Local Workspace"}
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-slate-500">
            commit: <span className="text-indigo-600 dark:text-indigo-400 font-bold">{project.commit?.slice(0, 8) || "HEAD"}</span>
          </div>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Sandbox Worktree Path</span>
          <div className="mt-1 font-mono text-[11px] text-indigo-600 dark:text-indigo-400 truncate" title={activeRun?.state?.worktree || `data/projects/${project.id}/worktrees/${runId}`}>
            {activeRun?.state?.worktree ? activeRun.state.worktree.split("/").slice(-4).join("/") : `worktrees/${runId}`}
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-slate-500 flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            <span>{activeRun?.state?.branch || "atlas/qe-sandbox"}</span>
          </div>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Synthesized Test Suites</span>
          <div className="mt-1 font-bold text-slate-800 dark:text-slate-200">
            {activeRun?.state?.tests?.length ? `${activeRun.state.tests.length} Suites Generated` : "Synthesizing suites..."}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
            tests/agentic_qe/ (1:1 assertions)
          </div>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Runner Verdict & Results</span>
          <div className="mt-1 flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200 truncate">
            {activeRun?.state?.results?.[0]?.verdict ? (
              <Badge tone={activeRun.state.results[0].verdict === "PASS" ? "emerald" : "rose"}>
                {activeRun.state.results[0].verdict}
              </Badge>
            ) : (
              <span className="text-slate-400 font-normal">Pending execution</span>
            )}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500 truncate" title={activeRun?.state?.execution_summary?.text || ""}>
            {activeRun?.state?.execution_summary?.text || "Runner awaiting gate trigger"}
          </div>
        </div>
      </div>
    </div>
  );
}
