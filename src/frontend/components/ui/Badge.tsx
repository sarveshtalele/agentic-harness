import { ReactNode } from "react";

const tones: Record<string, string> = {
  "NO NEW FAILURES": "amber", "NOT EXECUTED": "slate", "NEEDS REVIEW": "amber", queued: "slate", skipped: "slate", error: "rose", blocked: "rose", active: "emerald", disabled: "slate", enabled: "emerald", ok: "emerald", superseded: "slate", in_review: "amber", "in review": "amber", INCOMPLETE: "rose", approved: "emerald", completed: "emerald", PASS: "emerald", passed: "emerald", valid: "emerald", open: "amber",
  running: "indigo", waiting_approval: "amber", pending: "slate", draft: "slate", INCONCLUSIVE: "amber",
  rejected: "rose", failed: "rose", FAIL: "rose", interrupted: "rose", cancelled: "slate", critical: "rose", high: "rose", medium: "amber", low: "slate", info: "slate",
};
const toneClass: Record<string, string> = {
  emerald: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  amber: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  rose: "bg-rose-500/15 text-rose-700 dark:text-rose-400",
  indigo: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
  slate: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
};

export function Badge({ children, tone }: { children: ReactNode; tone?: string }) {
  const resolved = tone || tones[String(children)] || "slate";
  return <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${toneClass[resolved]}`}>{String(children).replace(/_/g, " ")}</span>;
}
