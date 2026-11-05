"use client";

import React, { useState, useEffect, useRef } from "react";
import { Terminal, Sparkles, Shield, RefreshCw, Cpu, Layers, BookOpen, Wrench, ChevronRight } from "lucide-react";

export interface SlashItem {
  id: string;
  command: string;
  displayName: string;
  description: string;
  category: string;
  source?: string;
  argumentHint?: string;
}

interface SlashCommandPaletteProps {
  query: string;
  onSelect: (command: string) => void;
  onClose: () => void;
  skills: Array<any>;
}

export const SlashCommandPalette: React.FC<SlashCommandPaletteProps> = ({
  query,
  onSelect,
  onClose,
  skills,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Core harness action commands
  const harnessCommands: SlashItem[] = [
    {
      id: "cmd-plan",
      command: "/plan",
      displayName: "/plan",
      description: "Formulate level-allocated test strategy & risk allocation (Gate 2)",
      category: "Harness Action",
      argumentHint: "<scope>",
    },
    {
      id: "cmd-execute",
      command: "/execute",
      displayName: "/execute",
      description: "Switch to Execute Mode to generate and run test suites (Gates 4-5)",
      category: "Harness Action",
      argumentHint: "<task>",
    },
    {
      id: "cmd-audit",
      command: "/audit",
      displayName: "/audit",
      description: "Run Cloudflare Security Audit on the codebase (CORS, IPC, injection)",
      category: "Harness Action",
    },
    {
      id: "cmd-heal",
      command: "/heal",
      displayName: "/heal",
      description: "Diagnose test failures and heal drifted locators preserving assertions",
      category: "Harness Action",
      argumentHint: "<file>",
    },
    {
      id: "cmd-skills",
      command: "/skills",
      displayName: "/skills",
      description: "Browse all 58 local machine skills installed across agentic-qe and Claude",
      category: "Harness Action",
    },
    {
      id: "cmd-gates",
      command: "/gates",
      displayName: "/gates",
      description: "View status and confidence scores of all 8 Quality Engineering Gates",
      category: "Harness Action",
    },
    {
      id: "cmd-todos",
      command: "/todos",
      displayName: "/todos",
      description: "Inspect active multi-step task ledger & milestone checklist",
      category: "Harness Action",
    },
    {
      id: "cmd-help",
      command: "/help",
      displayName: "/help",
      description: "Display harness user manual and slash command syntax",
      category: "Harness Action",
    },
  ];

  // Convert local machine skills into slash items
  const skillCommands: SlashItem[] = (skills || []).map((s) => ({
    id: `skill-${s.name}`,
    command: `/skill ${s.name}`,
    displayName: `/skill ${s.name}`,
    description: s.description || `Execute ${s.displayName}`,
    category: s.category || "Local Skill",
    source: s.source,
    argumentHint: s.argumentHint,
  }));

  const allItems: SlashItem[] = [...harnessCommands, ...skillCommands];

  // Filter based on input query (after '/')
  const filterText = query.replace(/^\//, "").toLowerCase().trim();
  const filtered = allItems.filter((item) => {
    if (!filterText) return true;
    const cmdNorm = item.command.replace(/^\//, "").toLowerCase();
    const nameNorm = item.displayName.toLowerCase();
    const descNorm = item.description.toLowerCase();
    const catNorm = item.category.toLowerCase();
    return (
      cmdNorm.includes(filterText) ||
      nameNorm.includes(filterText) ||
      descNorm.includes(filterText) ||
      catNorm.includes(filterText)
    );
  }).slice(0, 15); // limit to top 15 results for performance

  // Handle keyboard navigation
  useEffect(() => {
    setSelectedIndex(0);
  }, [filterText]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          onSelect(filtered[selectedIndex].command);
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [filtered, selectedIndex, onSelect, onClose]);

  if (filtered.length === 0) return null;

  return (
    <div
      ref={containerRef}
      className="absolute bottom-full left-0 right-0 mb-2 max-h-80 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-2xl z-50 text-xs font-mono backdrop-blur-md divide-y divide-[var(--border-subtle)]"
    >
      <div className="p-2 px-3 bg-[var(--bg-tertiary)] flex items-center justify-between text-[11px] text-[var(--text-muted)] select-none">
        <span className="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          <span>Slash Command & Local Skills Autocomplete ({filtered.length})</span>
        </span>
        <span className="text-[10px]">Use ↑↓ to navigate · Enter to select · ESC to dismiss</span>
      </div>

      <div className="py-1">
        {filtered.map((item, idx) => {
          const isSelected = idx === selectedIndex;
          return (
            <div
              key={item.id}
              onClick={() => onSelect(item.command)}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={`px-3 py-2 flex items-center justify-between cursor-pointer transition-colors ${
                isSelected
                  ? "bg-indigo-600/15 border-l-2 border-indigo-500 text-[var(--text-primary)]"
                  : "hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className={`font-semibold ${isSelected ? "text-indigo-400 font-bold" : "text-[var(--text-primary)]"}`}>
                  {item.displayName}
                </span>
                {item.argumentHint && (
                  <span className="text-[10px] text-[var(--text-muted)] font-mono">
                    {item.argumentHint}
                  </span>
                )}
                <span className="text-zinc-500 truncate text-[11px] font-sans">
                  — {item.description}
                </span>
              </div>

              <div className="flex items-center gap-1.5 ml-2 flex-shrink-0">
                {item.source && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-muted)]">
                    {item.source.split("(")[0].trim()}
                  </span>
                )}
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                  {item.category}
                </span>
                <ChevronRight className={`w-3.5 h-3.5 ${isSelected ? "text-indigo-400" : "text-transparent"}`} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
