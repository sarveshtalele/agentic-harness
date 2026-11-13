import { ChevronRight } from "lucide-react";

const STEPS = ["Gate 0: scope", "Read the sources", "Draft the BRD", "Independent review", "Gherkin check", "Gate 1: you sign"];

/** The steps a BA Studio run goes through. It states no status: each run's real progress is in its run panel below. */
export function LifecyclePipeline() {
  return (
    <ol className="mb-4 flex flex-wrap items-center gap-1 text-xs text-slate-600 dark:text-slate-300" aria-label="BA Studio steps">
      {STEPS.map((step, i) => (
        <li key={step} className="flex items-center gap-1">
          <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">{step}</span>
          {i < STEPS.length - 1 && <ChevronRight className="h-3 w-3 text-slate-400" />}
        </li>
      ))}
    </ol>
  );
}
