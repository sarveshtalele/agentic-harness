"use client";

import React, { useState } from "react";
import { ListTodo, BookOpen, ShieldCheck, Wrench, ChevronRight, ChevronLeft } from "lucide-react";
import { TodoItem, MagenticLedger, GateState } from "@/lib/maf/types";
import { TodoChecklist } from "./TodoChecklist";
import { MagenticLedgerView } from "./MagenticLedgerView";
import { QualityGatesTracker } from "./QualityGatesTracker";
import { MCPToolsExplorer } from "./MCPToolsExplorer";

interface ContextInspectorProps {
  todos: TodoItem[];
  ledger: MagenticLedger;
  gates: Record<number, GateState>;
  onToggleTodo?: (id: string, completed: boolean) => void;
  onAddTodo?: (title: string) => void;
  isOpen: boolean;
  onToggleOpen: () => void;
}

export const ContextInspector: React.FC<ContextInspectorProps> = ({
  todos,
  ledger,
  gates,
  onToggleTodo,
  onAddTodo,
  isOpen,
  onToggleOpen,
}) => {
  const [activeTab, setActiveTab] = useState<"todos" | "ledger" | "gates" | "tools">("todos");

  if (!isOpen) {
    return (
      <div className="border-l border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col items-center py-3 px-1.5 gap-3 select-none">
        <button
          onClick={onToggleOpen}
          className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          title="Open Context Inspector"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <button
          onClick={() => { onToggleOpen(); setActiveTab("todos"); }}
          className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-indigo-400"
          title="Todos"
        >
          <ListTodo className="w-4 h-4" />
        </button>
        <button
          onClick={() => { onToggleOpen(); setActiveTab("ledger"); }}
          className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          title="Magentic Ledger"
        >
          <BookOpen className="w-4 h-4" />
        </button>
        <button
          onClick={() => { onToggleOpen(); setActiveTab("gates"); }}
          className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          title="Quality Gates"
        >
          <ShieldCheck className="w-4 h-4" />
        </button>
        <button
          onClick={() => { onToggleOpen(); setActiveTab("tools"); }}
          className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          title="Tools & MCP"
        >
          <Wrench className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-80 md:w-96 border-l border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col h-full z-10 shadow-xl select-none">
      {/* Tab Navigation Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-tertiary)] px-2 py-1.5">
        <div className="flex items-center gap-1 overflow-x-auto text-xs font-mono">
          <button
            onClick={() => setActiveTab("todos")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
              activeTab === "todos"
                ? "bg-[var(--bg-primary)] text-indigo-400 font-semibold border border-[var(--border-color)] shadow-sm"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            <ListTodo className="w-3.5 h-3.5" /> Todos
          </button>

          <button
            onClick={() => setActiveTab("ledger")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
              activeTab === "ledger"
                ? "bg-[var(--bg-primary)] text-indigo-400 font-semibold border border-[var(--border-color)] shadow-sm"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" /> Ledger
          </button>

          <button
            onClick={() => setActiveTab("gates")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
              activeTab === "gates"
                ? "bg-[var(--bg-primary)] text-indigo-400 font-semibold border border-[var(--border-color)] shadow-sm"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" /> Gates
          </button>

          <button
            onClick={() => setActiveTab("tools")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
              activeTab === "tools"
                ? "bg-[var(--bg-primary)] text-indigo-400 font-semibold border border-[var(--border-color)] shadow-sm"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            <Wrench className="w-3.5 h-3.5" /> Tools
          </button>
        </div>

        <button
          onClick={onToggleOpen}
          className="p-1 rounded hover:bg-[var(--bg-secondary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          title="Collapse Context Inspector"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Tab Panels */}
      <div className="flex-1 overflow-hidden bg-[var(--bg-primary)]">
        {activeTab === "todos" && (
          <TodoChecklist
            todos={todos}
            onToggleTodo={onToggleTodo}
            onAddTodo={onAddTodo}
          />
        )}
        {activeTab === "ledger" && <MagenticLedgerView ledger={ledger} />}
        {activeTab === "gates" && <QualityGatesTracker gates={gates} />}
        {activeTab === "tools" && <MCPToolsExplorer />}
      </div>
    </div>
  );
};
