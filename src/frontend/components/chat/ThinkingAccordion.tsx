"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Brain, Clock } from "lucide-react";

interface ThinkingAccordionProps {
  thought: string;
  isStreaming?: boolean;
}

export const ThinkingAccordion: React.FC<ThinkingAccordionProps> = ({
  thought,
  isStreaming = false,
}) => {
  const [isOpen, setIsOpen] = useState(isStreaming);

  if (!thought) return null;

  return (
    <div className="my-2 border border-[var(--border-color)] bg-[var(--bg-secondary)] rounded-lg overflow-hidden text-xs shadow-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className={`w-3.5 h-3.5 text-indigo-400 ${isStreaming ? "animate-pulse" : ""}`} />
          <span className="font-mono font-medium text-[var(--text-primary)]">
            {isStreaming ? "Thinking & Planning..." : "Reasoning Process"}
          </span>
          {isStreaming && (
            <span className="inline-flex items-center gap-1 text-[10px] text-indigo-400 font-mono">
              <Clock className="w-2.5 h-2.5" /> Live
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-[var(--text-muted)] font-mono">
            {thought.split("\n").filter(Boolean).length} steps
          </span>
          {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" /> : <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />}
        </div>
      </button>

      {isOpen && (
        <div className="px-3 py-2.5 border-t border-[var(--border-subtle)] bg-[var(--bg-primary)]/80 text-[var(--text-secondary)] font-mono whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
          {thought}
        </div>
      )}
    </div>
  );
};
