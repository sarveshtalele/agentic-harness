"use client";

import React from "react";
import { User, Bot, Sparkles, Loader2 } from "lucide-react";
import { ChatMessage } from "@/lib/maf/types";
import { ThinkingAccordion } from "./ThinkingAccordion";
import { ToolCallCard } from "./ToolCallCard";
import { QualityGateApprovalCard } from "./QualityGateApprovalCard";
import { getAgent } from "@/lib/qe/agents";
import { Badge } from "../ui/Badge";

interface ChatMessageItemProps {
  message: ChatMessage;
  isStreaming?: boolean;
  onResolveApproval?: (approvalId: string, action: string) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  isStreaming = false,
  onResolveApproval,
}) => {
  const isUser = message.role === "user";
  const agent = message.agentId ? getAgent(message.agentId) : null;

  return (
    <div
      className={`py-4 px-4 sm:px-6 transition-colors border-b border-[var(--border-subtle)] ${
        isUser ? "bg-[var(--bg-secondary)]/50" : "bg-transparent"
      }`}
    >
      <div className="max-w-4xl mx-auto flex gap-3.5">
        {/* Avatar */}
        <div className="flex-shrink-0 pt-0.5">
          {isUser ? (
            <div className="w-8 h-8 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center text-[var(--text-primary)] shadow-sm">
              <User className="w-4 h-4" />
            </div>
          ) : (
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white shadow-md font-bold text-xs"
              style={{ backgroundColor: agent?.color || "#6366f1" }}
            >
              <Bot className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Message Body */}
        <div className="flex-1 min-w-0 space-y-2.5">
          {/* Header */}
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs text-[var(--text-primary)]">
              {isUser ? "You" : agent?.name || "MAF Harness Orchestrator"}
            </span>
            {!isUser && agent?.badge && (
              <Badge variant="outline" size="sm" className="text-[10px]">
                {agent.badge}
              </Badge>
            )}
            <span className="text-[10px] text-[var(--text-muted)] font-mono">
              {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>

          {/* Thinking Accordion (Internal reasoning steps) */}
          {message.thought && (
            <ThinkingAccordion thought={message.thought} isStreaming={isStreaming && !message.content} />
          )}

          {/* Tool Calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="space-y-1.5 my-2">
              {message.toolCalls.map((tc) => (
                <ToolCallCard key={tc.id} toolCall={tc} />
              ))}
            </div>
          )}

          {/* Quality Gate Card */}
          {message.gateApproval && (
            <QualityGateApprovalCard
              gate={message.gateApproval}
              approvalId={message.gateApproval.gateNumber ? `appr_${message.gateApproval.gateNumber}` : undefined}
              onDecision={(action) => {
                if (onResolveApproval && message.gateApproval?.gateNumber) {
                  onResolveApproval(`appr_${message.gateApproval.gateNumber}`, action);
                }
              }}
            />
          )}

          {/* Main Message Content */}
          {message.content ? (
            <div className="text-[var(--text-primary)] text-sm leading-relaxed font-sans max-w-none break-words whitespace-pre-wrap selection:bg-indigo-500/20">
              {message.content}
            </div>
          ) : isStreaming ? (
            <div className="flex items-center gap-2 py-2 text-indigo-400 font-mono text-xs">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Agent is reasoning and executing tools...</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
