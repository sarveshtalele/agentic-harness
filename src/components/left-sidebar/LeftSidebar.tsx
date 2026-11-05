"use client";

import React, { useState } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  Wrench,
  Bot,
  Server,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Cpu,
  Package,
  Sparkles,
} from "lucide-react";
import { Badge } from "../ui/Badge";
import { ThemeToggle } from "../theme/ThemeToggle";
import { SessionState } from "@/lib/maf/types";

export interface SessionItem {
  id: string;
  name: string;
  mode: string;
  activeAgentId: string;
  messagesCount: number;
  todosCount: number;
  updatedAt: number;
  createdAt: number;
}

interface LeftSidebarProps {
  sessions: SessionItem[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onOpenModelConfig: () => void;
  onOpenMCPSettings: () => void;
  sessionState: SessionState | null;
  agentsList: Array<{ id: string; name: string; role: string; badge: string; color: string }>;
  toolsUsed: Record<string, number>;
  pluginsList: Array<{ id: string; name: string; version: string; description: string; skills: string[]; author?: string }>;
  mcpServers: Array<{ id: string; name: string; status: string; transport: string }>;
  isOpen: boolean;
  onToggleOpen: () => void;
  currentModel: string;
  isModelConfigured: boolean;
  skillsList?: Array<any>;
  onSelectSkill?: (skillName: string) => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onOpenModelConfig,
  onOpenMCPSettings,
  sessionState,
  agentsList,
  toolsUsed,
  pluginsList,
  mcpServers,
  isOpen,
  onToggleOpen,
  currentModel,
  isModelConfigured,
  skillsList = [],
  onSelectSkill,
}) => {
  const [activeTab, setActiveTab] = useState<"history" | "tools" | "agents" | "plugins" | "mcp">("history");
  const [skillSearchQuery, setSkillSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  if (!isOpen) {
    return (
      <div className="border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col items-center py-3 px-1.5 gap-3 select-none">
        <button
          onClick={onToggleOpen}
          className="p-1.5 rounded hover:bg-[var(--border-color)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          title="Expand Sidebar"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={onNewSession}
          className="p-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white"
          title="New Session"
        >
          <Plus className="w-4 h-4" />
        </button>
        <ThemeToggle />
      </div>
    );
  }

  const totalToolInvocations = Object.values(toolsUsed).reduce((a, b) => a + b, 0);

  return (
    <div className="w-72 sm:w-80 border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col h-full select-none z-10 shadow-lg text-xs font-mono">
      {/* Brand Header */}
      <div className="p-3 border-b border-[var(--border-color)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-md">
            QE
          </div>
          <div>
            <h1 className="text-xs font-bold text-[var(--text-primary)] tracking-tight">
              Claude Code Desktop
            </h1>
            <span className="text-[10px] text-[var(--text-muted)] block">
              MAF 2.0 · {currentModel}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <button
            onClick={onToggleOpen}
            className="p-1.5 rounded hover:bg-[var(--border-color)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            title="Collapse Sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Model Configuration Warning Banner if unconfigured */}
      {!isModelConfigured && (
        <div
          onClick={onOpenModelConfig}
          className="p-2.5 bg-amber-950/40 border-b border-amber-600/40 text-amber-300 text-[11px] cursor-pointer hover:bg-amber-900/30 transition-colors flex items-center justify-between"
        >
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            Model not configured
          </span>
          <span className="underline font-sans">Set API Key</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="p-2.5 border-b border-[var(--border-color)] flex gap-1.5">
        <button
          onClick={onNewSession}
          className="flex-1 flex items-center justify-center gap-2 bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-[var(--text-primary)] px-3 py-1.5 rounded-md text-xs transition-colors shadow-sm"
        >
          <Plus className="w-3.5 h-3.5 text-indigo-400" />
          <span>New Session</span>
        </button>

        <button
          onClick={onOpenModelConfig}
          className="p-1.5 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-[var(--text-muted)] hover:text-indigo-400 transition-colors"
          title="Configure Model, Base URL & System Prompt"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs Header */}
      <div className="flex items-center border-b border-[var(--border-color)] bg-[var(--bg-primary)] px-1.5 py-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab("history")}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-colors ${
            activeTab === "history"
              ? "bg-[var(--bg-secondary)] text-indigo-400 font-semibold border border-[var(--border-color)]"
              : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          }`}
        >
          <MessageSquare className="w-3 h-3" /> History
        </button>

        <button
          onClick={() => setActiveTab("tools")}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-colors ${
            activeTab === "tools"
              ? "bg-[var(--bg-secondary)] text-indigo-400 font-semibold border border-[var(--border-color)]"
              : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Wrench className="w-3 h-3" /> Tools ({totalToolInvocations})
        </button>

        <button
          onClick={() => setActiveTab("plugins")}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-colors ${
            activeTab === "plugins"
              ? "bg-[var(--bg-secondary)] text-indigo-400 font-semibold border border-[var(--border-color)]"
              : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Package className="w-3 h-3 text-indigo-400" /> Plugins
        </button>

        <button
          onClick={() => setActiveTab("mcp")}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-colors ${
            activeTab === "mcp"
              ? "bg-[var(--bg-secondary)] text-indigo-400 font-semibold border border-[var(--border-color)]"
              : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Server className="w-3 h-3" /> MCP
        </button>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-2">
        {/* 1. History Tab */}
        {activeTab === "history" && (
          <div className="space-y-1">
            <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
              Persistent Sessions ({sessions.length})
            </div>
            {sessions.map((sess) => {
              const isActive = sess.id === activeSessionId;
              return (
                <div
                  key={sess.id}
                  onClick={() => onSelectSession(sess.id)}
                  className={`group flex items-center justify-between p-2 rounded-md transition-all cursor-pointer border ${
                    isActive
                      ? "bg-[var(--bg-tertiary)] border-indigo-500/60 text-[var(--text-primary)] font-medium shadow-sm"
                      : "bg-transparent border-transparent hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <MessageSquare
                      className={`w-3.5 h-3.5 flex-shrink-0 ${
                        isActive ? "text-indigo-400" : "text-[var(--text-muted)]"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs truncate">{sess.name}</p>
                      <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-[var(--text-muted)]">
                        <span>{sess.mode.toUpperCase()}</span>
                        <span>·</span>
                        <span>{sess.messagesCount} msgs</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(sess.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[var(--border-color)] text-[var(--text-muted)] hover:text-rose-400 transition-opacity"
                    title="Delete Session"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* 2. Tools Used Tab */}
        {activeTab === "tools" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                Active Tools & Usage
              </span>
              <Badge variant="purple" size="sm">
                {totalToolInvocations} Total Calls
              </Badge>
            </div>

            <div className="space-y-1.5">
              {[
                { name: "qe_discover_repo", desc: "AST & endpoint scanning (Gate 1)" },
                { name: "qe_extract_requirements", desc: "Spec & AC extraction" },
                { name: "qe_plan_strategy", desc: "Risk allocation (Gate 2)" },
                { name: "qe_design_cases", desc: "Deterministic cases (Gate 3)" },
                { name: "qe_generate_code", desc: "1:1 test code generation (Gate 4)" },
                { name: "qe_run_tests", desc: "Tokenized isolated execution (Gate 5)" },
                { name: "qe_diagnose_and_heal", desc: "Assertion preservation (Gate 6)" },
                { name: "qe_confidence_review", desc: "Citation verification (Gate 8)" },
                { name: "qe_security_audit", desc: "Cloudflare Security Audit" },
                { name: "todos_add", desc: "MAF Todo item creation" },
                { name: "todos_complete", desc: "MAF Todo milestone cleared" },
              ].map((tool) => {
                const count = toolsUsed[tool.name] || 0;
                return (
                  <div
                    key={tool.name}
                    className={`p-2 rounded border transition-colors ${
                      count > 0
                        ? "bg-[var(--bg-tertiary)] border-indigo-500/40"
                        : "bg-transparent border-[var(--border-color)]/60"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[var(--text-primary)]">
                        {tool.name}
                      </span>
                      <Badge variant={count > 0 ? "success" : "outline"} size="sm">
                        {count} calls
                      </Badge>
                    </div>
                    <p className="text-[10px] text-[var(--text-muted)] font-sans mt-0.5">
                      {tool.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 3. Plugins & Local Skills Tab (Distinct from MCP!) */}
        {activeTab === "plugins" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                Installed Plugins
              </span>
              <Badge variant="purple" size="sm">1 Active Plugin</Badge>
            </div>

            {pluginsList.map((p) => (
              <div
                key={p.id}
                className="p-3 rounded-lg border border-indigo-500/50 bg-[var(--bg-tertiary)] space-y-2 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold text-indigo-400">
                    <Package className="w-4 h-4" />
                    <span>{p.name}</span>
                  </div>
                  <Badge variant="success" size="sm">v{p.version}</Badge>
                </div>
                <p className="text-[10px] text-[var(--text-secondary)] font-sans leading-relaxed">
                  {p.description}
                </p>
                <div className="text-[10px] text-[var(--text-muted)] font-mono">
                  Author: <span className="text-[var(--text-primary)]">{p.author || "Sarvesh Talele"}</span>
                </div>

                <div className="pt-1.5 border-t border-[var(--border-color)]">
                  <span className="text-[10px] text-[var(--text-muted)] uppercase block mb-1">
                    Loaded Skills ({p.skills.length}):
                  </span>
                  <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                    {p.skills.map((s) => (
                      <button
                        key={s}
                        onClick={() => onSelectSkill && onSelectSkill(`/skill ${s}`)}
                        className="px-1.5 py-0.5 rounded bg-[var(--bg-primary)] hover:bg-indigo-600/20 border border-[var(--border-color)] text-[10px] text-indigo-300 font-mono transition-colors text-left"
                        title={`Run /skill ${s}`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {/* Dynamic Local Machine Skills Explorer */}
            <div className="pt-2 border-t border-[var(--border-color)] space-y-2">
              <div className="flex items-center justify-between px-1">
                <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-bold">
                  Local Skills Engine ({skillsList.length})
                </span>
                <span className="text-[9px] text-emerald-400 font-mono">● Host Synced</span>
              </div>

              {/* Search Skills Input */}
              <input
                type="text"
                value={skillSearchQuery}
                onChange={(e) => setSkillSearchQuery(e.target.value)}
                placeholder="Search local skills (e.g. qe-heal, caveman)..."
                className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-2.5 py-1 text-[11px] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-500 font-sans"
              />

              {/* Skills List */}
              <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                {skillsList
                  .filter((s) => {
                    const q = skillSearchQuery.toLowerCase();
                    return (
                      !q ||
                      s.name.toLowerCase().includes(q) ||
                      (s.description || "").toLowerCase().includes(q) ||
                      (s.category || "").toLowerCase().includes(q)
                    );
                  })
                  .slice(0, 30)
                  .map((sk) => (
                    <div
                      key={sk.name}
                      className="p-2 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)]/70 hover:border-indigo-500/50 transition-all space-y-1 group"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-bold text-[var(--text-primary)] truncate text-[11px]">
                          {sk.name}
                        </span>
                        <span className="text-[9px] px-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {sk.category}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--text-muted)] font-sans line-clamp-2 leading-tight">
                        {sk.description}
                      </p>
                      <div className="flex items-center justify-between pt-1 text-[9px] text-[var(--text-muted)]">
                        <span className="truncate max-w-[140px]">{sk.source}</span>
                        <button
                          onClick={() => onSelectSkill && onSelectSkill(`/skill ${sk.name}`)}
                          className="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors shadow-xs"
                        >
                          Run
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* 4. MCP Servers Tab (External Tools) */}
        {activeTab === "mcp" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                External MCP Servers ({mcpServers.length})
              </span>
              <button
                onClick={onOpenMCPSettings}
                className="text-[10px] text-indigo-400 hover:underline"
              >
                + Connect
              </button>
            </div>

            <div className="space-y-1.5">
              {mcpServers.map((srv) => (
                <div
                  key={srv.id}
                  className="p-2 rounded border border-[var(--border-color)] bg-[var(--bg-tertiary)]"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-[var(--text-primary)]">
                      {srv.name}
                    </span>
                    <Badge
                      variant={srv.status === "connected" ? "success" : "outline"}
                      size="sm"
                    >
                      {srv.status}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                    Transport: {srv.transport.toUpperCase()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Model Indicator */}
      <div className="p-2.5 border-t border-[var(--border-color)] bg-[var(--bg-primary)] flex items-center justify-between text-[11px]">
        <button
          onClick={onOpenModelConfig}
          className="flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-indigo-400 transition-colors"
        >
          <Cpu className="w-3.5 h-3.5 text-indigo-400" />
          <span className="truncate max-w-[140px]">{currentModel}</span>
        </button>

        <span
          className={`inline-flex items-center gap-1 text-[10px] font-mono ${
            isModelConfigured ? "text-emerald-400" : "text-amber-400"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isModelConfigured ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
            }`}
          />
          {isModelConfigured ? "Ready" : "Needs Key"}
        </span>
      </div>
    </div>
  );
};
