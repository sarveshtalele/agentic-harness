"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Terminal, Shield, RefreshCw, Layers } from "lucide-react";
import { StopButton } from "./StopButton";
import { Button } from "../ui/Button";
import { SlashCommandPalette } from "./SlashCommandPalette";

interface PromptInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  onStopExecution: () => void;
  mode: string;
  onToggleMode: (mode: "plan" | "execute") => void;
  activeAgentId: string;
  onSelectAgent: (agentId: string) => void;
  agents: Array<{ id: string; name: string; badge: string }>;
  skills?: Array<any>;
}

export const PromptInput: React.FC<PromptInputProps> = ({
  onSendMessage,
  isLoading,
  onStopExecution,
  mode,
  onToggleMode,
  activeAgentId,
  onSelectAgent,
  agents,
  skills = [],
}) => {
  const [input, setInput] = useState("");
  const [showPalette, setShowPalette] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
    // Show palette whenever input starts with / and hasn't had arguments yet or is searching
    setShowPalette(input.startsWith("/") && !input.includes(" "));
  }, [input]);

  // Support ESC key to stop execution or close palette
  useEffect(() => {
    const handleKeyDownGlobal = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showPalette) {
          setShowPalette(false);
        } else if (isLoading) {
          onStopExecution();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDownGlobal);
    return () => window.removeEventListener("keydown", handleKeyDownGlobal);
  }, [isLoading, showPalette, onStopExecution]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
    setShowPalette(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      if (showPalette) {
        const trimmed = input.trim();
        const noArgCommands = ["/skills", "/gates", "/audit", "/security-audit", "/help", "/todos", "/clear"];
        if (noArgCommands.includes(trimmed)) {
          e.preventDefault();
          handleSubmit();
          return;
        }
        return;
      }
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSlashCommandSelect = (cmd: string) => {
    const noArgCommands = ["/skills", "/gates", "/audit", "/security-audit", "/help", "/todos", "/clear"];
    if (noArgCommands.includes(cmd)) {
      onSendMessage(cmd);
      setInput("");
      setShowPalette(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    } else {
      setInput(cmd + " ");
      setShowPalette(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  return (
    <div className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)] p-3 sm:p-4 backdrop-blur-md relative select-none">
      <div className="max-w-4xl mx-auto space-y-2">
        {/* Quick Slash Commands Pills */}
        <div className="flex items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 min-w-0">
            <span className="text-[var(--text-muted)] font-mono text-[11px] flex-shrink-0">Quick:</span>
            <button
              type="button"
              onClick={() => handleSlashCommandSelect("/plan")}
              className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-indigo-400 font-mono text-[11px] transition-colors flex items-center gap-1 flex-shrink-0"
            >
              <Terminal className="w-2.5 h-2.5" /> /plan
            </button>
            <button
              type="button"
              onClick={() => handleSlashCommandSelect("/execute")}
              className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-emerald-400 font-mono text-[11px] transition-colors flex items-center gap-1 flex-shrink-0"
            >
              <Sparkles className="w-2.5 h-2.5" /> /execute
            </button>
            <button
              type="button"
              onClick={() => handleSlashCommandSelect("/skills")}
              className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-cyan-400 font-mono text-[11px] transition-colors flex items-center gap-1 flex-shrink-0"
            >
              <Layers className="w-2.5 h-2.5" /> /skills ({skills.length || 58})
            </button>
            <button
              type="button"
              onClick={() => handleSlashCommandSelect("/security-audit")}
              className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-rose-400 font-mono text-[11px] transition-colors flex items-center gap-1 flex-shrink-0"
            >
              <Shield className="w-2.5 h-2.5" /> /audit
            </button>
            <button
              type="button"
              onClick={() => handleSlashCommandSelect("/heal")}
              className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-amber-400 font-mono text-[11px] transition-colors flex items-center gap-1 flex-shrink-0"
            >
              <RefreshCw className="w-2.5 h-2.5" /> /heal
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[10px] text-[var(--text-muted)] font-mono flex-shrink-0">
            <span>Type <kbd className="px-1 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-indigo-400 font-bold">/</kbd> for full command palette</span>
          </div>
        </div>

        {/* Textarea Composer Container with floating SlashCommandPalette */}
        <div className="relative">
          {showPalette && (
            <SlashCommandPalette
              query={input}
              onSelect={handleSlashCommandSelect}
              onClose={() => setShowPalette(false)}
              skills={skills}
            />
          )}

          <div className="flex items-end gap-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl p-2.5 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all shadow-inner">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Instruct MAF harness, run test analysis, or enter / for skills..."
              disabled={isLoading}
              className="w-full bg-transparent text-[var(--text-primary)] placeholder-[var(--text-muted)] text-sm focus:outline-none resize-none font-sans max-h-44 py-1 px-2"
            />

            {isLoading ? (
              <StopButton onStop={onStopExecution} />
            ) : (
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => handleSubmit()}
                disabled={!input.trim()}
                className="rounded-lg h-8 px-3 flex-shrink-0 bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
              >
                <Send className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>

        {/* Footer Info */}
        <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] px-1 font-mono">
          <span>Enter to send · Shift+Enter for newline</span>
          <span>Microsoft Agent Framework v2.0 · AG-UI & CopilotKit</span>
        </div>
      </div>
    </div>
  );
};
