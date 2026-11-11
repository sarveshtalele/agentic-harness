import { CheckCircle2, Sparkles } from "lucide-react";

export function LifecyclePipeline() {
  return (
    <div className="mb-4 rounded-xl border border-indigo-100 bg-indigo-50/40 p-3 dark:border-indigo-900/40 dark:bg-indigo-950/20">
      <div className="mb-2 flex items-center justify-between text-xs font-semibold text-indigo-900 dark:text-indigo-200">
        <span className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
          Autonomous BA Lifecycle Pipeline
        </span>
        <span className="font-mono text-[11px] text-indigo-600 dark:text-indigo-400">Gate 0 ➔ Gate 1 Continuous Verification</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-6 text-[11px]">
        <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">0</span>
          <span className="truncate font-medium">Gate 0: Scope</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">1</span>
          <span className="truncate font-medium">Context Ingest</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">2</span>
          <span className="truncate font-medium">Draft 10 Secs</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">3</span>
          <span className="truncate font-medium">Confidence Score</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">4</span>
          <span className="truncate font-medium">Gherkin Oracles</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/80 p-1.5 shadow-2xs dark:border-emerald-800/60 dark:bg-emerald-950/40">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <span className="truncate font-bold text-emerald-800 dark:text-emerald-300">Gate 1 Approved</span>
        </div>
      </div>
    </div>
  );
}
