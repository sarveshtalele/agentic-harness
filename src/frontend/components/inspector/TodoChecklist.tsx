"use client";

import React, { useState } from "react";
import { CheckSquare, Square, Plus, ListTodo, CheckCircle2 } from "lucide-react";
import { TodoItem } from "@/lib/maf/types";
import { Badge } from "../harness-ui/Badge";

interface TodoChecklistProps {
  todos: TodoItem[];
  onToggleTodo?: (id: string, completed: boolean) => void;
  onAddTodo?: (title: string) => void;
}

export const TodoChecklist: React.FC<TodoChecklistProps> = ({
  todos,
  onToggleTodo,
  onAddTodo,
}) => {
  const [newTitle, setNewTitle] = useState("");
  const [filter, setFilter] = useState<"all" | "pending" | "completed">("all");

  const completedCount = todos.filter((t) => t.status === "completed").length;
  const totalCount = todos.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const filteredTodos = todos.filter((t) => {
    if (filter === "pending") return t.status !== "completed";
    if (filter === "completed") return t.status === "completed";
    return true;
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !onAddTodo) return;
    onAddTodo(newTitle.trim());
    setNewTitle("");
  };

  return (
    <div className="flex flex-col h-full text-xs font-mono">
      {/* Header & Progress Bar */}
      <div className="p-3 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
            <ListTodo className="w-4 h-4 text-indigo-400" />
            <span>Active Todo Checklist</span>
          </div>
          <Badge variant={progressPercent === 100 ? "success" : "purple"} size="sm">
            {completedCount}/{totalCount} ({progressPercent}%)
          </Badge>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-[var(--bg-tertiary)] h-1.5 rounded-full overflow-hidden border border-[var(--border-color)]">
          <div
            className="bg-indigo-500 h-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1.5 pt-1">
          {(["all", "pending", "completed"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold transition-colors ${
                filter === f
                  ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/40"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Todo Items List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredTodos.length === 0 ? (
          <div className="py-12 text-center text-[var(--text-muted)] font-mono text-xs">
            <p>No todos found in this filter.</p>
            <p className="text-[10px] mt-1 text-[var(--text-muted)]">
              Use <code className="bg-[var(--bg-secondary)] px-1 rounded">/plan</code> or ask the agent to add tasks.
            </p>
          </div>
        ) : (
          filteredTodos.map((todo) => {
            const isDone = todo.status === "completed";
            return (
              <div
                key={todo.id}
                className={`p-2.5 rounded-lg border transition-all ${
                  isDone
                    ? "bg-[var(--bg-secondary)]/40 border-[var(--border-subtle)] text-[var(--text-muted)]"
                    : "bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-primary)] shadow-sm"
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <button
                    onClick={() => onToggleTodo && onToggleTodo(todo.id, !isDone)}
                    className="mt-0.5 text-indigo-400 hover:text-indigo-300 transition-colors flex-shrink-0"
                  >
                    {isDone ? (
                      <CheckSquare className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Square className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                  </button>

                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-sans leading-relaxed ${isDone ? "line-through text-[var(--text-muted)]" : "text-[var(--text-primary)]"}`}>
                      {todo.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[var(--text-muted)] font-mono">
                      {todo.agentId && (
                        <span className="px-1.5 py-0.2 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-indigo-400">
                          {todo.agentId}
                        </span>
                      )}
                      <span>
                        {new Date(todo.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Manual Todo Input */}
      {onAddTodo && (
        <form onSubmit={handleAdd} className="p-2 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex gap-1.5">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Add new task..."
            className="flex-1 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-2.5 py-1.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-500 font-sans"
          />
          <button
            type="submit"
            disabled={!newTitle.trim()}
            className="p-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </form>
      )}
    </div>
  );
};
