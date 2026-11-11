import { Info, ShieldAlert } from "lucide-react";
import { Badge, Card, Empty } from "../../components/ui";
import { when } from "../../lib/api";
import { GUARDRAIL_FLAGS } from "./guardrailFlags";

export function GuardrailEvents({ events }: { events: any[] }) {
  return (
    <div className="mt-6">
      <Card title={<span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-500" /> Recent Guardrail Events ({events.length})</span>}>
        {events.length ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 max-h-[580px] overflow-y-auto pr-2">
            {events.map((e) => {
              const isInjection = e.kind?.includes("prompt_injection") || e.detail?.includes("Ignore all previous");
              const isSecret = e.kind?.includes("secret") || e.action === "redacted";
              const tone = isInjection ? "rose" : isSecret ? "amber" : "indigo";
              const badgeLabel = e.action ? e.action.toUpperCase() : "INTERCEPTED";
              const matchedFlag = GUARDRAIL_FLAGS.find((f) =>
                isInjection
                  ? f.key === "prompt_injection"
                  : isSecret
                  ? f.key === "secret"
                  : f.key === e.kind
              ) || GUARDRAIL_FLAGS[0];

              return (
                <div
                  key={e.id}
                  className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs transition hover:border-indigo-400 dark:border-slate-800 dark:bg-[#0b1329]"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                        <ShieldAlert className={`h-3.5 w-3.5 ${isInjection ? "text-rose-500" : isSecret ? "text-amber-500" : "text-indigo-500"}`} />
                        <span className="capitalize">{e.kind ? e.kind.replace(/_/g, " ") : "Policy Guardrail"}</span>
                        <div className="relative group/cardtip">
                          <Info className="h-3 w-3 text-slate-400 cursor-pointer hover:text-indigo-600" />
                          <div className="absolute left-4 bottom-full z-50 hidden group-hover/cardtip:block w-64 rounded-xl border border-slate-200 bg-white p-2.5 shadow-xl dark:border-slate-800 dark:bg-[#0b1329] dark:text-slate-200 text-[10px] leading-relaxed">
                            <p className="font-bold text-slate-900 dark:text-white mb-0.5">{matchedFlag.name}</p>
                            <p className="text-slate-600 dark:text-slate-400">{matchedFlag.summary}</p>
                          </div>
                        </div>
                      </div>
                      <Badge tone={tone}>{badgeLabel}</Badge>
                    </div>

                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        {e.agent || "runtime-guard"}
                      </span>
                    </div>

                    <div className="rounded-lg border border-slate-100 bg-slate-50 p-2 font-mono text-[11px] text-slate-700 dark:border-slate-800/80 dark:bg-slate-950/70 dark:text-slate-300 overflow-x-auto max-h-24 whitespace-pre-wrap break-all">
                      {e.detail}
                    </div>
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[10px] text-slate-400 dark:border-slate-800/60">
                    <span className="flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                      <span>Zero-Trust Demarcation</span>
                    </span>
                    <span>{when(e.created_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty title="No guardrail events recorded" />
        )}
      </Card>
    </div>
  );
}
