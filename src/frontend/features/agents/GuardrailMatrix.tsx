import { Info, ShieldCheck } from "lucide-react";
import { Badge, Card } from "../../components/ui";
import { GUARDRAIL_FLAGS } from "./guardrailFlags";

export function GuardrailMatrix() {
  return (
    <div className="mt-6">
      <Card
        title={
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-indigo-500" />
            Guardrail Security Flags & Threat Mitigation Matrix
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <tr>
                <th className="pb-2.5 font-semibold">Security Flag</th>
                <th className="pb-2.5 font-semibold">Severity</th>
                <th className="pb-2.5 font-semibold">Action Enforced</th>
                <th className="pb-2.5 font-semibold">Trigger Condition</th>
                <th className="pb-2.5 font-semibold">Mitigation Strategy</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {GUARDRAIL_FLAGS.map((flag) => {
                const tone =
                  flag.severity === "critical"
                    ? "rose"
                    : flag.severity === "high"
                    ? "amber"
                    : flag.severity === "medium"
                    ? "indigo"
                    : "slate";

                return (
                  <tr
                    key={flag.key}
                    className="group hover:bg-slate-50/60 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <td className="py-2.5 pr-3 font-medium text-slate-900 dark:text-slate-100">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold">{flag.name}</span>
                        <div className="relative flex items-center group/tooltip">
                          <Info className="h-3.5 w-3.5 text-slate-400 group-hover/tooltip:text-indigo-600 dark:text-slate-500 dark:group-hover/tooltip:text-indigo-400 cursor-pointer" />
                          {/* Hover Tooltip */}
                          <div className="absolute left-6 bottom-full z-50 hidden group-hover/tooltip:block w-72 rounded-xl border border-slate-200 bg-white p-3 shadow-xl dark:border-slate-800 dark:bg-[#0b1329] dark:text-slate-200 text-[11px] leading-relaxed">
                            <p className="font-bold text-slate-900 dark:text-white mb-1">
                              {flag.name} ({flag.action})
                            </p>
                            <p className="text-slate-600 dark:text-slate-400 mb-2">
                              {flag.summary}
                            </p>
                            <div className="border-t border-slate-100 pt-1.5 dark:border-slate-800 space-y-1">
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Trigger: </span>
                                <span className="text-slate-500 dark:text-slate-400">{flag.condition}</span>
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Defense: </span>
                                <span className="text-slate-500 dark:text-slate-400">{flag.mitigation}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <Badge tone={tone}>{flag.severity.toUpperCase()}</Badge>
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        {flag.action}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-400 max-w-xs">
                      {flag.condition}
                    </td>
                    <td className="py-2.5 text-slate-500 dark:text-slate-400 max-w-sm">
                      {flag.mitigation}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
