import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";

export function NextStepBanner({ step }: { step: { label: string; href: string } }) {
  return (
    <Link
      href={step.href}
      className="group flex flex-col gap-3 rounded-2xl border border-indigo-500/40 bg-gradient-to-r from-indigo-500/10 via-indigo-500/5 to-transparent p-4 transition-all hover:border-indigo-500 hover:shadow-md sm:flex-row sm:items-center sm:justify-between dark:border-indigo-500/30 dark:from-indigo-950/30"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm group-hover:scale-105 transition-transform">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider block">
            Recommended Action
          </span>
          <span className="text-sm font-bold text-slate-900 dark:text-white">
            {step.label}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition-transform">
        <span>Proceed</span>
        <ArrowRight className="h-4 w-4" />
      </div>
    </Link>
  );
}
