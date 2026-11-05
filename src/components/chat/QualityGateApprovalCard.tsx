"use client";

import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, XCircle, Zap, ExternalLink } from "lucide-react";
import { GateApprovalInfo } from "@/lib/maf/types";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

interface QualityGateApprovalCardProps {
  approvalId?: string;
  gate: GateApprovalInfo;
  onDecision?: (decision: "approve" | "reject" | "always_approve", feedback?: string) => void;
}

export const QualityGateApprovalCard: React.FC<QualityGateApprovalCardProps> = ({
  approvalId,
  gate,
  onDecision,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [decided, setDecided] = useState<string | null>(gate.status !== "pending" ? gate.status : null);
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);

  const handleAction = async (action: "approve" | "reject" | "always_approve") => {
    if (action === "reject" && !showFeedback) {
      setShowFeedback(true);
      return;
    }

    setSubmitting(true);
    try {
      if (approvalId) {
        await fetch("/api/approvals", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approvalId, action, feedback }),
        });
      }
      setDecided(action);
      if (onDecision) {
        onDecision(action, feedback);
      }
    } catch (e) {
      console.error("Failed to submit gate decision:", e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="my-3 border-2 border-indigo-500/50 bg-indigo-950/20 rounded-lg p-4 shadow-lg backdrop-blur-sm">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-md bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs uppercase tracking-wider text-indigo-300 font-semibold">
                Quality Gate {gate.gateNumber}
              </span>
              <Badge variant="purple" size="sm">
                Score: {gate.confidenceScore}/100
              </Badge>
            </div>
            <h4 className="text-sm font-semibold text-zinc-100">{gate.gateName}</h4>
          </div>
        </div>

        {decided && (
          <Badge
            variant={decided === "approve" || decided === "always_approve" ? "success" : "error"}
            size="md"
          >
            {decided.toUpperCase()}
          </Badge>
        )}
      </div>

      <div className="text-xs text-zinc-300 bg-black/40 rounded border border-zinc-800 p-3 mb-3 font-mono leading-relaxed">
        <p className="mb-2 text-zinc-200">{gate.artifactSummary}</p>
        {gate.evidenceCitations && gate.evidenceCitations.length > 0 && (
          <div className="text-[11px] text-zinc-400 border-t border-zinc-800/80 pt-2 mt-2">
            <span className="text-zinc-500 block mb-1">Ground Truth Repository Evidence:</span>
            <div className="flex flex-wrap gap-1.5">
              {gate.evidenceCitations.map((cit, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 bg-zinc-900 px-2 py-0.5 rounded text-indigo-300 border border-zinc-800"
                >
                  <ExternalLink className="w-2.5 h-2.5" /> {cit}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {showFeedback && (
        <div className="mb-3">
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Specify reason for revision / flaws to fix..."
            className="w-full bg-zinc-950 border border-rose-800/80 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-rose-500 font-mono"
          />
        </div>
      )}

      {!decided && (
        <div className="flex items-center justify-end gap-2 pt-1 border-t border-indigo-900/40">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleAction("reject")}
            loading={submitting}
            className="text-rose-400 hover:text-rose-300 hover:bg-rose-950/30"
          >
            <XCircle className="w-3.5 h-3.5" /> Request Revision
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleAction("always_approve")}
            loading={submitting}
            className="text-zinc-300"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" /> Always Auto-Approve Gate
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => handleAction("approve")}
            loading={submitting}
            className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
          >
            <CheckCircle2 className="w-3.5 h-3.5" /> Approve & Proceed
          </Button>
        </div>
      )}
    </div>
  );
};
