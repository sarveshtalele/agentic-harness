import { AlertTriangle, Lock, ShieldAlert, ShieldCheck } from "lucide-react";
import { Badge, Card } from "../../components/ui";

export function ActiveGuardrails() {
  return (
    <Card title="Active Security Guardrails & Enforcements">
      <div className="grid gap-3 md:grid-cols-2 text-xs">
        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/40 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              Prompt Injection Demarcation
            </span>
            <Badge tone="emerald">Active</Badge>
          </div>
          <p className="text-slate-500 dark:text-slate-400">
            Skill text is framed as `&lt;skill&gt;` and `&lt;reference&gt;` blocks and the task follows `TASK:` (core/skills.py, maf/runtime.py). Repository and document text is treated as data, never as instructions.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/40 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <Lock className="h-4 w-4 text-indigo-500" />
              Zero-Trust Assertion Preservation
            </span>
            <Badge tone="indigo">Enforced</Badge>
          </div>
          <p className="text-slate-500 dark:text-slate-400">
            Healing and test generation reject changes that delete or weaken assertions, add skips, or use trivial checks (qe/execution.py assertions_preserved and the weakening rules).
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/40 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <ShieldAlert className="h-4 w-4 text-amber-500" />
              Sandbox Boundary &amp; Path Traversal
            </span>
            <Badge tone="amber">Strict</Badge>
          </div>
          <p className="text-slate-500 dark:text-slate-400">
            Canonical realpath boundary isolation with NUL byte guards. Strict directory containment prevents path traversal and writes to protected folders (`.git`, `.venv`, `.qe`).
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/40 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-rose-500" />
              Secret Scanner &amp; Redaction
            </span>
            <Badge tone="rose">Real-time</Badge>
          </div>
          <p className="text-slate-500 dark:text-slate-400">
            Shannon entropy calculation and multi-vendor regex scanning (GitHub tokens, AWS, GCP, Slack, private keys) auto-redacting sensitive credentials before model consumption.
          </p>
        </div>
      </div>
    </Card>
  );
}
