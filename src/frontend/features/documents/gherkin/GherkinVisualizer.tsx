"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { FeatureHeader } from "./FeatureHeader";
import { GherkinScenario, parseGherkinContent } from "./parse";
import { ScenarioCard } from "./ScenarioCard";
import { formatStepText, stepBadgeStyle } from "./steps";

export function GherkinVisualizer({ content }: { content: string }) {
  const [filterQuery, setFilterQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedScenarios, setExpandedScenarios] = useState<Record<string, boolean>>({});

  const parsed = useMemo(() => parseGherkinContent(content), [content]);

  const toggleScenario = (id: string) => {
    setExpandedScenarios((prev) => ({
      ...prev,
      [id]: prev[id] === undefined ? false : !prev[id],
    }));
  };

  const copyScenario = (sc: GherkinScenario) => {
    const lines = [
      sc.tags.join(" "),
      `${sc.type}: ${sc.name}`,
      ...sc.steps.map((s) => `  ${s.keyword} ${s.text}`),
    ];
    if (sc.examples) {
      lines.push("  Examples:");
      lines.push(`    | ${sc.examples.header.join(" | ")} |`);
      sc.examples.rows.forEach((r) => lines.push(`    | ${r.join(" | ")} |`));
    }
    navigator.clipboard.writeText(lines.filter(Boolean).join("\n"));
    setCopiedId(sc.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredScenarios = useMemo(() => {
    if (!filterQuery.trim()) return parsed.scenarios;
    const q = filterQuery.toLowerCase();
    return parsed.scenarios.filter(
      (sc) =>
        sc.name.toLowerCase().includes(q) ||
        sc.tags.some((t) => t.toLowerCase().includes(q)) ||
        sc.steps.some((st) => st.text.toLowerCase().includes(q))
    );
  }, [parsed.scenarios, filterQuery]);

  return (
    <div className="space-y-4">
      <FeatureHeader parsed={parsed} />

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Filter scenarios by name, tag, or step..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="w-full rounded-xl border border-slate-700/80 bg-slate-900/80 pl-9 pr-3 py-2 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div className="text-xs text-slate-400">
          Showing {filteredScenarios.length} of {parsed.scenarios.length} scenarios
        </div>
      </div>

      {/* Background Section (if present) */}
      {parsed.background && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <span className="inline-block rounded bg-slate-800 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-3">
            Background Setup
          </span>
          <div className="space-y-2">
            {parsed.background.steps.map((st, i) => (
              <div key={i} className="flex items-start gap-2.5 text-xs sm:text-sm">
                <span className={`rounded px-2 py-0.5 text-[11px] font-bold shrink-0 ${stepBadgeStyle(st.keyword)}`}>
                  {st.keyword}
                </span>
                <span className="text-slate-300 leading-relaxed">{formatStepText(st.text)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenarios Grid */}
      <div className="space-y-3">
        {filteredScenarios.map((sc, scIdx) => (
          <ScenarioCard key={sc.id} sc={sc} scIdx={scIdx} isExpanded={expandedScenarios[sc.id] ?? true} copiedId={copiedId} onToggle={toggleScenario} onCopy={copyScenario} />
        ))}
      </div>
    </div>
  );
}
