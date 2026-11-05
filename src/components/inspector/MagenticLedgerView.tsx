"use client";

import React from "react";
import { BookOpen, CheckCircle, Clock, AlertTriangle, ShieldCheck } from "lucide-react";
import { MagenticLedger } from "@/lib/maf/types";
import { Badge } from "../ui/Badge";

interface MagenticLedgerViewProps {
  ledger: MagenticLedger;
}

export const MagenticLedgerView: React.FC<MagenticLedgerViewProps> = ({ ledger }) => {
  return (
    <div className="flex flex-col h-full text-xs overflow-y-auto p-3 space-y-4 font-mono">
      {/* Stall Warning if triggered */}
      {ledger.isStalled && (
        <div className="p-3 rounded-lg border border-amber-600/60 bg-amber-950/40 text-amber-200 space-y-1">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>MAF Magentic Stall Detected</span>
          </div>
          <p className="text-[11px] font-sans">
            Harness detected {ledger.stallCount} attempts without state progression. Human intervention or revised guidance is requested.
          </p>
        </div>
      )}

      {/* Task Ledger Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
          <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
          <span>Task Ledger (Objective & Subgoals)</span>
        </div>

        <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2">
          <div>
            <span className="text-[var(--text-muted)] text-[10px] uppercase tracking-wider block">Overall Goal</span>
            <p className="text-[var(--text-primary)] text-xs font-sans mt-0.5">{ledger.taskLedger.goal}</p>
          </div>

          <div className="border-t border-[var(--border-subtle)] pt-2">
            <span className="text-[var(--text-muted)] text-[10px] uppercase tracking-wider block mb-1.5">
              Subgoal Breakdown
            </span>
            <div className="space-y-1.5">
              {ledger.taskLedger.subgoals.map((sg) => (
                <div
                  key={sg.id}
                  className={`flex items-start gap-2 p-1.5 rounded text-[11px] ${
                    sg.done ? "bg-emerald-950/20 text-[var(--text-muted)]" : "bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
                  }`}
                >
                  {sg.done ? (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="min-w-0 flex-1">
                    <span className={sg.done ? "line-through" : "font-medium"}>
                      {sg.title}
                    </span>
                    {sg.assignedAgent && (
                      <span className="block text-[10px] text-[var(--text-muted)] font-mono mt-0.5">
                        Specialist: {sg.assignedAgent}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {ledger.taskLedger.constraints.length > 0 && (
            <div className="border-t border-[var(--border-subtle)] pt-2">
              <span className="text-[var(--text-muted)] text-[10px] uppercase tracking-wider block mb-1">
                Active Constraints
              </span>
              <ul className="list-disc list-inside space-y-0.5 text-[var(--text-secondary)] text-[10px]">
                {ledger.taskLedger.constraints.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Progress Ledger Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Progress Ledger</span>
        </div>

        <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2">
          <div>
            <span className="text-[var(--text-muted)] text-[10px] uppercase tracking-wider block">Current Subgoal</span>
            <p className="text-indigo-400 font-medium text-xs mt-0.5">
              {ledger.progressLedger.currentSubgoal}
            </p>
          </div>

          <div className="border-t border-[var(--border-subtle)] pt-2">
            <span className="text-[var(--text-muted)] text-[10px] uppercase tracking-wider block mb-1">
              Completed Milestones ({ledger.progressLedger.completedSteps.length})
            </span>
            {ledger.progressLedger.completedSteps.length === 0 ? (
              <span className="text-[var(--text-muted)] text-[10px]">No steps completed yet.</span>
            ) : (
              <div className="space-y-1">
                {ledger.progressLedger.completedSteps.map((step, idx) => (
                  <div key={idx} className="text-[10px] text-[var(--text-secondary)] flex items-center gap-1.5">
                    <CheckCircle className="w-2.5 h-2.5 text-emerald-500 flex-shrink-0" />
                    <span className="truncate">{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
