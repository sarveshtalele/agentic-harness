"use client";

import React, { useRef, useEffect } from "react";
import {
  Sparkles,
  Terminal,
  Shield,
  Layers,
  Download,
  Trash2,
  Cpu,
  RefreshCw,
} from "lucide-react";
import { ChatMessage, AIAgentDefinition } from "@/lib/maf/types";
import { ChatMessageItem } from "./ChatMessageItem";
import { PromptInput } from "./PromptInput";
import { Badge } from "../harness-ui/Badge";
import { Button } from "../harness-ui/Button";

interface ChatContainerProps {
  sessionName: string;
  workingDir: string;
  mode: string;
  onToggleMode: (mode: "plan" | "execute") => void;
  activeAgent: AIAgentDefinition;
  onSelectAgent: (agentId: string) => void;
  agents: Array<{ id: string; name: string; badge: string }>;
  messages: ChatMessage[];
  streamingThought?: string;
  streamingContent?: string;
  isStreaming: boolean;
  onSendMessage: (message: string) => void;
  onStopExecution: () => void;
  onExportSession: () => void;
  onClearSession: () => void;
  onToggleInspector: () => void;
  isInspectorOpen: boolean;
  currentModel: string;
  isModelConfigured?: boolean;
  onOpenModelConfig?: () => void;
  skills?: Array<any>;
  onResolveApproval?: (approvalId: string, action: string) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  sessionName,
  workingDir,
  mode,
  onToggleMode,
  activeAgent,
  onSelectAgent,
  agents,
  messages,
  streamingThought,
  streamingContent,
  isStreaming,
  onSendMessage,
  onStopExecution,
  onExportSession,
  onClearSession,
  onToggleInspector,
  isInspectorOpen,
  currentModel,
  isModelConfigured = true,
  onOpenModelConfig,
  skills = [],
  onResolveApproval,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent, streamingThought]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg-primary)] relative overflow-hidden text-xs">
      {/* Top Header Bar */}
      <div className="h-14 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 flex items-center justify-between backdrop-blur-md z-10 select-none">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-sm text-[var(--text-primary)] truncate max-w-xs sm:max-w-md">
                {sessionName}
              </h2>
              <Badge variant="outline" size="sm" className="hidden sm:inline-flex text-[10px] flex-shrink-0">
                {workingDir.split("/").pop() || "workspace"}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)] font-mono mt-0.5 truncate max-w-md">
              <span className="flex-shrink-0">Specialist:</span>
              <span className="text-[var(--text-primary)] font-medium truncate">{activeAgent.name}</span>
              <span>·</span>
              <span className="text-indigo-400 flex-shrink-0">{activeAgent.badge}</span>
              <span>·</span>
              <span className="text-[var(--text-muted)] flex-shrink-0">{currentModel}</span>
            </div>
          </div>
        </div>

        {/* Right Header Controls */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Mode Toggle Button */}
          <button
            onClick={() => onToggleMode(mode === "plan" ? "execute" : "plan")}
            className={`hidden md:inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-mono text-xs font-semibold border transition-all ${
              mode === "plan"
                ? "bg-indigo-950/80 border-indigo-500/70 text-indigo-300"
                : "bg-emerald-950/80 border-emerald-500/70 text-emerald-300"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                mode === "plan" ? "bg-indigo-400" : "bg-emerald-400"
              }`}
            />
            {mode === "plan" ? "PLAN MODE" : "EXECUTE MODE"}
          </button>

          <Button
            variant="ghost"
            size="xs"
            onClick={onExportSession}
            title="Export Session JSON"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <Download className="w-3.5 h-3.5" />
          </Button>

          <Button
            variant="ghost"
            size="xs"
            onClick={onClearSession}
            title="Clear Messages"
            className="text-[var(--text-muted)] hover:text-rose-400"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>

          <Button
            variant="outline"
            size="xs"
            onClick={onToggleInspector}
            className={`text-xs gap-1 font-mono ${
              isInspectorOpen
                ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-[var(--border-color)]"
                : "text-[var(--text-muted)]"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Inspector</span>
          </Button>
        </div>
      </div>

      {/* High-Visibility Enterprise Alert Banner when Model is Unconfigured */}
      {!isModelConfigured && (
        <div
          data-testid="model-unconfigured-banner"
          className="bg-amber-950/70 border-b border-amber-500/40 px-4 py-2 flex items-center justify-between text-amber-200 text-xs font-mono shadow-inner z-10"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
            <span className="truncate">
              <strong className="text-amber-100 font-semibold">Model Not Configured:</strong> No API Key is set for <code className="bg-black/40 px-1 py-0.5 rounded text-amber-300">{currentModel}</code>.
            </span>
          </div>
          <button
            onClick={onOpenModelConfig}
            className="ml-3 px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white font-medium rounded text-[11px] transition-colors shadow-sm flex-shrink-0"
          >
            Configure Key
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto divide-y divide-[var(--border-subtle)]">
        {messages.length === 0 && !isStreaming ? (
          <div className="max-w-2xl mx-auto py-16 px-4 text-center space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mx-auto shadow-inner">
              <Sparkles className="w-6 h-6" />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
                Claude Code Desktop QE Harness
              </h3>
              <p className="text-xs text-[var(--text-secondary)] max-w-md mx-auto leading-relaxed">
                Powered by Autonomous Agentic QE Engine. Connected to live model:{" "}
                <strong className="text-indigo-400">{currentModel}</strong>.
              </p>
            </div>

            {/* Quick action buttons */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left max-w-lg mx-auto pt-2 font-mono text-xs">
              <button
                onClick={() =>
                  onSendMessage("Discover repository AST, map dependencies, and extract public API endpoints.")
                }
                className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors group"
              >
                <div className="font-semibold text-[var(--text-primary)] group-hover:text-indigo-400 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                  <span>1. Discover Repository</span>
                </div>
                <p className="text-[11px] text-[var(--text-muted)] font-sans mt-1">
                  Scan workspace files and detect framework conventions (Gate 1).
                </p>
              </button>

              <button
                onClick={() =>
                  onSendMessage("/plan Formulate comprehensive risk-allocated test strategy across Unit, API, and E2E.")
                }
                className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors group"
              >
                <div className="font-semibold text-[var(--text-primary)] group-hover:text-indigo-400 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-indigo-400" />
                  <span>2. Plan Test Strategy</span>
                </div>
                <p className="text-[11px] text-[var(--text-muted)] font-sans mt-1">
                  Level allocation without duplicate scenarios (Gate 2).
                </p>
              </button>

              <button
                onClick={() =>
                  onSendMessage("/execute Generate 1:1 Vitest and Playwright test code for approved design cases.")
                }
                className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors group"
              >
                <div className="font-semibold text-[var(--text-primary)] group-hover:text-emerald-400 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-emerald-400" />
                  <span>3. Generate Test Code</span>
                </div>
                <p className="text-[11px] text-[var(--text-muted)] font-sans mt-1">
                  Produce compilable test files mapped 1:1 to designs (Gate 4).
                </p>
              </button>

              <button
                onClick={() =>
                  onSendMessage("/heal Analyze failure traces, repair drifted selectors, and verify assertions.")
                }
                className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors group"
              >
                <div className="font-semibold text-[var(--text-primary)] group-hover:text-amber-400 flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
                  <span>4. Heal Broken Tests</span>
                </div>
                <p className="text-[11px] text-[var(--text-muted)] font-sans mt-1">
                  Autonomous healing with strict assertion preservation (Gate 6).
                </p>
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                onResolveApproval={onResolveApproval}
              />
            ))}

            {/* In-flight streaming message */}
            {isStreaming && (
              <ChatMessageItem
                message={{
                  id: "streaming-in-flight",
                  role: "assistant",
                  content: streamingContent || "",
                  thought: streamingThought,
                  agentId: activeAgent.id,
                  createdAt: 0,
                }}
                isStreaming={true}
                onResolveApproval={onResolveApproval}
              />
            )}
          </>
        )}
      </div>

      {/* Bottom Prompt Composer */}
      <PromptInput
        onSendMessage={onSendMessage}
        isLoading={isStreaming}
        onStopExecution={onStopExecution}
        mode={mode}
        onToggleMode={onToggleMode}
        activeAgentId={activeAgent.id}
        onSelectAgent={onSelectAgent}
        agents={agents}
        skills={skills}
      />
    </div>
  );
};
