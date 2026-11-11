import { Check, Copy, Wrench, X } from "lucide-react";
import { Button } from "../../components/ui";
import { generateStepByStepGuide } from "./lib";

type Props = { finding: any; copiedCode: boolean; setCopiedCode: (v: boolean) => void; onClose: () => void; onApply: () => void };

export function GuideModal({ finding, copiedCode, setCopiedCode, onClose, onApply }: Props) {
  const guide = generateStepByStepGuide(finding);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-2xl max-h-[90vh] flex flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-[#0b1329] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <Wrench className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                End-to-End Bug Remediation Guide
              </h3>
              <span className="font-mono text-[11px] text-slate-500">
                {finding.file}:{finding.line}
              </span>
            </div>
          </div>
          <button
            onClick={() => onClose()}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {/* Step 1: Diagnosis & Root Cause */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-bold mb-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-950 text-[11px]">1</span>
              <span>Phase 1: Root Cause & Impact Diagnosis</span>
            </div>
            <p className="text-slate-700 dark:text-slate-300 font-medium">
              {guide.phase1_diagnosis.summary}
            </p>
            <p className="mt-1 text-slate-500">
              <strong>Root Cause:</strong> {guide.phase1_diagnosis.rootCause}
            </p>
            <p className="mt-1 text-rose-600 dark:text-rose-400">
              <strong>Vulnerability Impact:</strong> {guide.phase1_diagnosis.impact}
            </p>
          </div>

          {/* Step 2: Code Patch Diff */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex items-center justify-between text-indigo-600 dark:text-indigo-400 font-bold mb-1.5">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-950 text-[11px]">2</span>
                <span>Phase 2: Code Remediation Diff</span>
              </div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(guide.phase2_code_diff.remediatedCode);
                  setCopiedCode(true);
                  setTimeout(() => setCopiedCode(false), 2000);
                }}
                className="flex items-center gap-1 font-mono text-[10px] text-slate-500 hover:text-indigo-600"
              >
                {copiedCode ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                <span>{copiedCode ? "Copied" : "Copy Patch"}</span>
              </button>
            </div>
            <pre className="mt-2 rounded-lg bg-slate-950 p-2.5 font-mono text-[11px] text-emerald-400 overflow-x-auto whitespace-pre-wrap">
              {guide.phase2_code_diff.remediatedCode}
            </pre>
          </div>

          {/* Step 3: Sandbox Verification */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-bold mb-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-950 text-[11px]">3</span>
              <span>Phase 3: Automated Sandbox Verification Command</span>
            </div>
            <div className="rounded-lg bg-slate-950 p-2 font-mono text-[11px] text-indigo-300">
              $ {guide.phase3_verification.command}
            </div>
            <p className="mt-1 text-slate-500">
              <strong>Expected Result:</strong> {guide.phase3_verification.expectedOutcome}
            </p>
          </div>

          {/* Step 4: Quality Gate Compliance */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-bold mb-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-950 text-[11px]">4</span>
              <span>Phase 4: Quality Gate Compliance</span>
            </div>
            <p className="text-slate-700 dark:text-slate-300">
              <strong>Target Gate:</strong> {guide.phase4_gate_compliance.gate}
            </p>
            <p className="mt-0.5 text-slate-500">
              {guide.phase4_gate_compliance.status}
            </p>
          </div>

          {/* Step 5: Bug Fix Reviewer Evaluation */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3.5 dark:border-emerald-500/20 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between text-emerald-700 dark:text-emerald-400 font-bold mb-1.5">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950 text-[11px]">5</span>
                <span>Phase 5: {guide.phase5_bug_fix_reviewer.agent} Confidence Audit</span>
              </div>
              <span className="rounded-md bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-400 border border-emerald-500/30">
                {guide.phase5_bug_fix_reviewer.confidenceScore}% Confidence · {guide.phase5_bug_fix_reviewer.verdict}
              </span>
            </div>
            <p className="text-slate-700 dark:text-slate-300">
              <strong>Assertion Preservation:</strong> {guide.phase5_bug_fix_reviewer.assertionPreservation}
            </p>
            <p className="mt-0.5 text-slate-500">
              <strong>Reviewer Note:</strong> {guide.phase5_bug_fix_reviewer.recommendation}
            </p>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="flex items-center justify-between border-t border-slate-200 p-4 dark:border-slate-800">
          <Button variant="secondary" onClick={() => onClose()}>
            Close
          </Button>
          <Button
            variant="primary"
            onClick={onApply}
          >
            <Wrench className="h-4 w-4" /> Apply Fix on Branch
          </Button>
        </div>
      </div>
    </div>
  );
}
