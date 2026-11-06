"use client";

import React, { useState, useMemo } from "react";
import { Check, Copy, ChevronDown, ChevronRight, Search, Sparkles, Filter, Code, Layers } from "lucide-react";

interface GherkinStep {
  keyword: string; // Given, When, Then, And, But
  text: string;
  table?: string[][];
  docString?: string;
}

interface GherkinScenario {
  id: string;
  type: "Scenario" | "Scenario Outline";
  name: string;
  tags: string[];
  steps: GherkinStep[];
  examples?: {
    header: string[];
    rows: string[][];
  };
}

interface ParsedGherkin {
  featureName: string;
  featureDescription: string;
  featureTags: string[];
  background?: {
    steps: GherkinStep[];
  };
  scenarios: GherkinScenario[];
}

export function parseGherkinContent(raw: string): ParsedGherkin {
  const lines = raw.split("\n");
  const parsed: ParsedGherkin = {
    featureName: "Feature Specification",
    featureDescription: "",
    featureTags: [],
    scenarios: [],
  };

  let currentTags: string[] = [];
  let currentScenario: GherkinScenario | null = null;
  let inBackground = false;
  let backgroundSteps: GherkinStep[] = [];
  let inExamples = false;
  let exampleRows: string[][] = [];
  let featureFound = false;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    // Tags
    if (trimmed.startsWith("@")) {
      const tags = trimmed.split(/\s+/).filter((t) => t.startsWith("@"));
      currentTags.push(...tags);
      continue;
    }

    // Feature
    if (/^Feature:/i.test(trimmed)) {
      featureFound = true;
      parsed.featureName = trimmed.replace(/^Feature:\s*/i, "").trim();
      parsed.featureTags = [...currentTags];
      currentTags = [];
      // Collect description until next block
      const descLines: string[] = [];
      i++;
      while (i < lines.length) {
        const l = lines[i].trim();
        if (/^(Background:|Scenario:|Scenario Outline:|@)/i.test(l)) {
          i--;
          break;
        }
        if (l) descLines.push(l);
        i++;
      }
      parsed.featureDescription = descLines.join("\n");
      continue;
    }

    // Background
    if (/^Background:/i.test(trimmed)) {
      inBackground = true;
      inExamples = false;
      currentScenario = null;
      continue;
    }

    // Scenario / Scenario Outline
    if (/^(Scenario|Scenario Outline):/i.test(trimmed)) {
      if (currentScenario) {
        if (inExamples && exampleRows.length > 0) {
          currentScenario.examples = {
            header: exampleRows[0] || [],
            rows: exampleRows.slice(1),
          };
        }
        parsed.scenarios.push(currentScenario);
      }
      inBackground = false;
      inExamples = false;
      exampleRows = [];

      const isOutline = /^Scenario Outline:/i.test(trimmed);
      const name = trimmed.replace(/^(Scenario Outline|Scenario):\s*/i, "").trim();
      currentScenario = {
        id: `sc_${parsed.scenarios.length + 1}`,
        type: isOutline ? "Scenario Outline" : "Scenario",
        name: name || `Scenario ${parsed.scenarios.length + 1}`,
        tags: [...currentTags],
        steps: [],
      };
      currentTags = [];
      continue;
    }

    // Examples
    if (/^Examples:/i.test(trimmed)) {
      inExamples = true;
      exampleRows = [];
      continue;
    }

    // Table rows (in Examples or Step DataTables)
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      const row = trimmed
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim());
      if (inExamples && currentScenario) {
        exampleRows.push(row);
      } else if (currentScenario && currentScenario.steps.length > 0) {
        const lastStep = currentScenario.steps[currentScenario.steps.length - 1];
        lastStep.table = lastStep.table || [];
        lastStep.table.push(row);
      }
      continue;
    }

    // Steps
    const stepMatch = trimmed.match(/^(Given|When|Then|And|But)\s+(.*)$/i);
    if (stepMatch) {
      const keyword = stepMatch[1].toUpperCase();
      const text = stepMatch[2];
      const step: GherkinStep = { keyword, text };

      if (inBackground) {
        backgroundSteps.push(step);
      } else if (currentScenario) {
        currentScenario.steps.push(step);
      }
      continue;
    }
  }

  if (currentScenario) {
    if (inExamples && exampleRows.length > 0) {
      currentScenario.examples = {
        header: exampleRows[0] || [],
        rows: exampleRows.slice(1),
      };
    }
    parsed.scenarios.push(currentScenario);
  }

  if (backgroundSteps.length > 0) {
    parsed.background = { steps: backgroundSteps };
  }

  return parsed;
}

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

  const stepBadgeStyle = (kw: string) => {
    switch (kw) {
      case "GIVEN":
        return "bg-sky-500/15 text-sky-400 border border-sky-500/30";
      case "WHEN":
        return "bg-amber-500/15 text-amber-400 border border-amber-500/30";
      case "THEN":
        return "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
      case "AND":
      case "BUT":
        return "bg-purple-500/15 text-purple-400 border border-purple-500/30";
      default:
        return "bg-slate-700/40 text-slate-300 border border-slate-600";
    }
  };

  // Helper to format step text: highlight quoted strings and variables
  const formatStepText = (text: string) => {
    const parts = text.split(/("[^"]*"|<[^>]*>)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('"') && part.endsWith('"')) {
        return (
          <span key={idx} className="font-mono text-indigo-300 font-semibold bg-indigo-950/40 px-1 py-0.5 rounded border border-indigo-800/40">
            {part}
          </span>
        );
      }
      if (part.startsWith("<") && part.endsWith(">")) {
        return (
          <span key={idx} className="font-mono text-amber-300 font-bold bg-amber-950/40 px-1 py-0.5 rounded border border-amber-800/40">
            {part}
          </span>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="space-y-4">
      {/* Feature Header Card */}
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
        {filteredScenarios.map((sc, scIdx) => {
          const isExpanded = expandedScenarios[sc.id] ?? true;
          return (
            <div
              key={sc.id}
              className="overflow-hidden rounded-xl border border-slate-800/90 bg-slate-900/50 hover:border-slate-700 transition shadow-sm"
            >
              {/* Scenario Header */}
              <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-800/40 px-4 py-3">
                <div
                  className="flex items-center gap-2.5 flex-1 min-w-0 cursor-pointer select-none"
                  onClick={() => toggleScenario(sc.id)}
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
                    onClick={() => copyScenario(sc)}
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
        })}
      </div>
    </div>
  );
}
