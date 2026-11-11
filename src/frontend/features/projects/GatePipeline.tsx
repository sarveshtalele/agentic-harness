import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Badge } from "../../components/ui";
import { Approver } from "../../components/Approver";

export function GatePipeline({ gates, base }: { gates: any[]; base: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Quality Engineering Gate Progression</h3>
          <p className="text-xs text-slate-500">Strict human-in-the-loop stage sign-offs enforce non-weakened assertions</p>
        </div>
        <Link href={`${base}/qe`} className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400 flex items-center gap-1">
          QE Studio <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {gates.map((g: any) => {
          const isApproved = g.status === "approved";
          const isPending = g.status === "pending";
          return (
            <Link
              key={g.gate}
              href={`${base}/qe`}
              className={`flex flex-col justify-between rounded-xl border p-3 transition-all hover:scale-[1.02] ${
                isApproved
                  ? "border-emerald-500/30 bg-emerald-50/40 dark:border-emerald-500/20 dark:bg-emerald-950/20"
                  : isPending
                  ? "border-amber-500/30 bg-amber-50/40 dark:border-amber-500/20 dark:bg-amber-950/20"
                  : "border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/40"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                  G{g.gate}
                </span>
                <Badge tone={isApproved ? "emerald" : isPending ? "amber" : "slate"}>
                  {g.status}
                </Badge>
              </div>
              <div className="my-2">
                <span className="block text-xs font-bold text-slate-800 dark:text-slate-200 line-clamp-1">
                  {g.name}
                </span>
                <span className="block text-[11px] text-slate-500 truncate mt-0.5">
                  {g.decided_by ? <Approver item={g} /> : "Automated Review"}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
