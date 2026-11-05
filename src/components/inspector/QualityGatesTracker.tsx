"use client";

import React from "react";
import { ShieldCheck, CheckCircle2, Clock, AlertCircle, FileCheck2 } from "lucide-react";
import { GateState } from "@/lib/maf/types";
import { Badge } from "../ui/Badge";

interface QualityGatesTrackerProps {
  gates: Record<number, GateState>;
}

export const QualityGatesTracker: React.FC<QualityGatesTrackerProps> = ({ gates }) => {
  const gateDefinitions: Array<{ number: number; name: string; criteria: string; persona: string }> = [
    { number: 1, name: "Discovery & Requirements", criteria: "AST parsed, public routes identified, spec extracted", persona: "repo-intelligence-analyst" },
    { number: 2, name: "Test Strategy & Risk", criteria: "Tiers allocated (Unit/API/E2E), risk ranked P0-P2", persona: "principal-test-architect" },
    { number: 3, name: "Deterministic Case Design", criteria: "Concrete fixtures, non-overlapping boundary cases", persona: "test-design-architect" },
    { number: 4, name: "1:1 Code Generation", criteria: "Compilable test source, zero mocks for system under test", persona: "test-automation-engineer" },
    { number: 5, name: "Isolated Test Execution", criteria: "Subprocess allowlisted execution, JUnit XML parsed", persona: "qa-execution-engineer" },
    { number: 6, name: "Assertion-Preserving Healing", criteria: "Never weaken or delete assertions during healing", persona: "defect-diagnostician" },
    { number: 7, name: "Coverage & Risk Audit", criteria: "100% critical paths verified, zero orphaned test files", persona: "coverage-auditor" },
    { number: 8, name: "Production Release Sign-off", criteria: "Independent confidence verification (0-100) based on citations", persona: "confidence-reviewer" },
  ];

  const gateList = gateDefinitions.map((def) => {
    const state = gates[def.number] || {
      gateNumber: def.number,
      name: def.name,
      status: "not_started",
      score: null,
      updatedAt: Date.now(),
    };
    return { ...def, ...state };
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge variant="success" size="sm" className="gap-1"><CheckCircle2 className="w-2.5 h-2.5" /> Approved</Badge>;
      case "pending":
        return <Badge variant="warning" size="sm" className="gap-1"><Clock className="w-2.5 h-2.5" /> Pending Review</Badge>;
      case "rejected":
        return <Badge variant="error" size="sm" className="gap-1"><AlertCircle className="w-2.5 h-2.5" /> Rejected</Badge>;
      default:
        return <Badge variant="outline" size="sm">Not Started</Badge>;
    }
  };

  return (
    <div className="flex flex-col h-full text-xs overflow-y-auto p-3 space-y-3 font-mono">
      <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
          <ShieldCheck className="w-4 h-4 text-indigo-400" />
          <span>8 Verifiable Quality Gates</span>
        </div>
        <Badge variant="purple" size="sm">
          {gateList.filter((g) => g.status === "approved").length}/8 Cleared
        </Badge>
      </div>

      <div className="space-y-2.5">
        {gateList.map((g) => {
          const isApproved = g.status === "approved";
          return (
            <div
              key={g.number}
              className={`p-3 rounded-lg border transition-all ${
                isApproved
                  ? "bg-emerald-950/15 border-emerald-500/40"
                  : g.status === "pending"
                  ? "bg-amber-950/15 border-amber-500/40"
                  : "bg-[var(--bg-secondary)] border-[var(--border-color)]"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
                    <span className="w-5 h-5 rounded bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center text-[10px] font-bold">
                      G{g.number}
                    </span>
                    <span className="font-sans text-xs">{g.name}</span>
                  </div>
                  <p className="text-[10px] text-[var(--text-muted)] font-sans mt-1">
                    {g.criteria}
                  </p>
                </div>
                {getStatusBadge(g.status)}
              </div>

              <div className="mt-2.5 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                <span className="text-indigo-400">{g.persona}</span>
                {g.score !== null && (
                  <span className="font-bold text-[var(--text-primary)]">Confidence: {g.score}%</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
