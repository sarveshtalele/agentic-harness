import { Code, Layers } from "lucide-react";
import { ParsedGherkin } from "./parse";

export function FeatureHeader({ parsed }: { parsed: ParsedGherkin }) {
  return (
    <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-slate-900/40 to-purple-950/30 p-5 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-indigo-500/20 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-indigo-300 border border-indigo-500/30">
              Feature
            </span>
            {parsed.featureTags.map((tag) => (
              <span key={tag} className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300 border border-slate-700">
                {tag}
              </span>
            ))}
          </div>
          <h2 className="mt-2 text-lg font-bold text-white tracking-tight">{parsed.featureName}</h2>
          {parsed.featureDescription && (
            <p className="mt-1.5 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">{parsed.featureDescription}</p>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1.5 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <Layers className="h-3.5 w-3.5 text-indigo-400" />
            <b className="text-white">{parsed.scenarios.length}</b> Scenarios
          </span>
          <span className="flex items-center gap-1.5 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <Code className="h-3.5 w-3.5 text-emerald-400" />
            <b className="text-white">
              {parsed.scenarios.reduce((sum, sc) => sum + sc.steps.length, 0)}
            </b> Steps
          </span>
        </div>
      </div>
    </div>
  );
}
