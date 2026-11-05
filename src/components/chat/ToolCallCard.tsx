"use client";

import React, { useState } from "react";
import { Wrench, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";
import { ToolCall } from "@/lib/maf/types";
import { Badge } from "../ui/Badge";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  const [expanded, setExpanded] = useState(false);

  const isRunning = toolCall.status === "running" || toolCall.status === "pending";
  const isCompleted = toolCall.status === "completed" || toolCall.result !== undefined;
  const isFailed = toolCall.status === "failed" || toolCall.error !== undefined;

  const getStatusBadge = () => {
    if (isRunning) {
      return (
        <Badge variant="warning" size="sm" className="gap-1 animate-pulse">
          <Loader2 className="w-2.5 h-2.5 animate-spin" /> executing
        </Badge>
      );
    }
    if (isCompleted) {
      return (
        <Badge variant="success" size="sm" className="gap-1">
          <CheckCircle2 className="w-2.5 h-2.5" /> completed
        </Badge>
      );
    }
    if (isFailed) {
      return (
        <Badge variant="error" size="sm" className="gap-1">
          <XCircle className="w-2.5 h-2.5" /> failed
        </Badge>
      );
    }
    return <Badge variant="outline" size="sm">{toolCall.status}</Badge>;
  };

  return (
    <div className="my-2 border border-[var(--border-color)] bg-[var(--bg-secondary)] rounded-lg overflow-hidden text-xs shadow-sm">
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors select-none"
      >
        <div className="flex items-center gap-2">
          <Wrench className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-mono font-medium text-[var(--text-primary)]">{toolCall.name}</span>
          {toolCall.gateNumber && (
            <Badge variant="purple" size="sm" className="gap-1">
              <ShieldCheck className="w-2.5 h-2.5" /> Gate {toolCall.gateNumber}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge()}
          {expanded ? <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" /> : <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-[var(--border-subtle)] p-3 bg-[var(--bg-primary)] font-mono space-y-2 text-[11px]">
          <div>
            <span className="text-[var(--text-muted)] block mb-1">Parameters:</span>
            <pre className="bg-[var(--bg-secondary)] p-2 rounded border border-[var(--border-color)] text-[var(--text-secondary)] overflow-x-auto max-h-40">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>

          {toolCall.result && (
            <div>
              <span className="text-[var(--text-muted)] block mb-1">Output Result:</span>
              <pre className="bg-[var(--bg-secondary)] p-2 rounded border border-[var(--border-color)] text-emerald-400 overflow-x-auto max-h-52">
                {typeof toolCall.result === "string"
                  ? toolCall.result
                  : JSON.stringify(toolCall.result, null, 2)}
              </pre>
            </div>
          )}

          {toolCall.error && (
            <div>
              <span className="text-rose-400 block mb-1">Error:</span>
              <pre className="bg-rose-950/20 p-2 rounded border border-rose-900/40 text-rose-300 overflow-x-auto">
                {toolCall.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
