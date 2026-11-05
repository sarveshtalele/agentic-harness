"use client";

import React from "react";
import { Plus, MessageSquare, Trash2, Bot, Settings, Layers, ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";
import { HarnessMode } from "@/lib/maf/types";
import { Badge } from "../ui/Badge";
import { getAllAgents } from "@/lib/qe/agents";

export interface SessionSummary {
  id: string;
  name: string;
  mode: HarnessMode;
  activeAgentId: string;
  messagesCount: number;
  todosCount: number;
  updatedAt: number;
  createdAt: number;
}

interface SessionSidebarProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onOpenSettings: () => void;
  isOpen: boolean;
  onToggleOpen: () => void;
}

export const SessionSidebar: React.FC<SessionSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onOpenSettings,
  isOpen,
  onToggleOpen,
}) => {
  const agents = getAllAgents();

  if (!isOpen) {
    return (
      <div className="border-r border-zinc-800 bg-zinc-950 flex flex-col items-center py-3 px-1.5 gap-3">
        <button
          onClick={onToggleOpen}
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
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
      </div>
    );
  }

  return (
    <div className="w-64 sm:w-72 border-r border-zinc-800 bg-zinc-950 flex flex-col h-full select-none z-10 shadow-xl">
      {/* Brand Header */}
      <div className="p-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-md">
            QE
          </div>
          <div>
            <h1 className="text-xs font-bold text-zinc-100 tracking-tight">Agentic QE Harness</h1>
            <span className="text-[10px] text-zinc-500 font-mono block">MAF 2.0 Engine</span>
          </div>
        </div>

        <button
          onClick={onToggleOpen}
          className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
          title="Collapse Sidebar"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* New Session Button */}
      <div className="p-3 border-b border-zinc-800/80">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-200 px-3 py-2 rounded-md font-mono text-xs transition-colors shadow-sm"
        >
          <Plus className="w-3.5 h-3.5 text-indigo-400" />
          <span>New QE Session</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-zinc-500">
          Persistent Sessions ({sessions.length})
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-6 text-zinc-600 font-mono text-xs">
            No active sessions.
          </div>
        ) : (
          sessions.map((sess) => {
            const isActive = sess.id === activeSessionId;
            return (
              <div
                key={sess.id}
                onClick={() => onSelectSession(sess.id)}
                className={`group flex items-center justify-between p-2 rounded-md transition-all cursor-pointer border ${
                  isActive
                    ? "bg-zinc-900 border-indigo-500/50 text-zinc-100 shadow-sm"
                    : "bg-transparent border-transparent hover:bg-zinc-900/50 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-indigo-400" : "text-zinc-500"}`} />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium truncate">{sess.name}</p>
                    <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-zinc-500 font-mono">
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
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition-opacity"
                  title="Delete Session"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Agents Roster Quick View */}
      <div className="p-3 border-t border-zinc-800/80 bg-black/20 text-xs">
        <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-2">
          <span>Inbuilt QE Agents</span>
          <Badge variant="purple" size="sm">8 Active</Badge>
        </div>
        <div className="flex flex-wrap gap-1">
          {agents.map((ag) => (
            <span
              key={ag.id}
              className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-400 truncate max-w-[120px]"
              title={`${ag.name}: ${ag.description}`}
            >
              {ag.name.split(" ")[0]}
            </span>
          ))}
        </div>
      </div>

      {/* Footer Settings */}
      <div className="p-2 border-t border-zinc-800 flex items-center justify-between text-xs">
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200 px-2 py-1.5 rounded hover:bg-zinc-900 transition-colors"
        >
          <Settings className="w-3.5 h-3.5" />
          <span className="font-mono text-[11px]">MCP & Settings</span>
        </button>

        <span className="text-[10px] font-mono text-emerald-400/90 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Ready
        </span>
      </div>
    </div>
  );
};
