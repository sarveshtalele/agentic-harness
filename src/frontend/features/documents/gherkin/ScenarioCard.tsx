import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";
import { GherkinScenario } from "./parse";
import { formatStepText, stepBadgeStyle } from "./steps";

type Props = { sc: GherkinScenario; scIdx: number; isExpanded: boolean; copiedId: string | null; onToggle: (id: string) => void; onCopy: (sc: GherkinScenario) => void };

export function ScenarioCard({ sc, scIdx, isExpanded, copiedId, onToggle, onCopy }: Props) {
  return (
    <div
      className="overflow-hidden rounded-xl border border-slate-800/90 bg-slate-900/50 hover:border-slate-700 transition shadow-sm"
    >
      {/* Scenario Header */}
      <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-800/40 px-4 py-3">
        <div
          className="flex items-center gap-2.5 flex-1 min-w-0 cursor-pointer select-none"
          onClick={() => onToggle(sc.id)}
        >
          <button className="text-slate-400 hover:text-white">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <span className="font-mono text-xs text-indigo-400 font-semibold">
            #{String(scIdx + 1).padStart(2, "0")}
          </span>
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${
            sc.type === "Scenario Outline"
              ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
              : "bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
          }`}>
            {sc.type}
          </span>
          <h3 className="text-sm font-semibold text-white truncate">{sc.name}</h3>
        </div>

        <div className="flex items-center gap-2">
          {sc.tags.map((t) => (
            <span key={t} className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 border border-slate-700">
              {t}
            </span>
          ))}
          <button
            onClick={() => onCopy(sc)}
            title="Copy scenario"
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-700 text-slate-400 hover:border-indigo-500 hover:text-white transition"
          >
            {copiedId === sc.id ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Scenario Body */}
      {isExpanded && (
        <div className="p-4 space-y-3">
          {/* Steps */}
          <div className="space-y-2">
            {sc.steps.map((st, stIdx) => (
              <div key={stIdx} className="flex items-start gap-2.5 text-xs sm:text-sm">
                <span className={`rounded px-2 py-0.5 text-[11px] font-bold shrink-0 ${stepBadgeStyle(st.keyword)}`}>
                  {st.keyword}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-slate-300 leading-relaxed">{formatStepText(st.text)}</p>
                  {/* Step Data Table if present */}
                  {st.table && (
                    <div className="mt-2 overflow-x-auto rounded-lg border border-slate-800 bg-[#070d1f] p-2">
                      <table className="w-full text-left text-xs font-mono">
                        <tbody>
                          {st.table.map((row, rIdx) => (
                            <tr key={rIdx} className={rIdx === 0 ? "font-bold text-indigo-300 border-b border-slate-800" : "text-slate-300 border-b border-slate-850"}>
                              {row.map((col, cIdx) => (
                                <td key={cIdx} className="px-2 py-1">{col}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Examples Table */}
          {sc.examples && (
            <div className="mt-4 pt-3 border-t border-slate-800/80">
              <span className="block text-[11px] font-bold uppercase tracking-wider text-amber-400 mb-2">
                Examples Parameter Matrix
              </span>
              <div className="overflow-x-auto rounded-lg border border-slate-800 bg-[#070d1f] shadow-inner">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="bg-slate-800/80 border-b border-slate-700/80 text-amber-300">
                      {sc.examples.header.map((head, hIdx) => (
                        <th key={hIdx} className="px-3 py-2 font-bold">{head}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {sc.examples.rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-800/30 transition text-slate-300">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="px-3 py-1.5">{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
