import { Card } from "../../components/ui";
import { FindingCard } from "./FindingCard";

type Props = { findings: any[]; counts: Record<string, number>; severity: string; setSeverity: (s: string) => void; shown: any[]; onGuide: (f: any) => void; onFix: (f: any) => void; onDismiss: (id: string) => void };

export function FindingsList({ findings, counts, severity, setSeverity, shown, onGuide, onFix, onDismiss }: Props) {
  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <span>Open Findings ({findings.length})</span>
          {findings.length > 0 && (
            <span className="text-xs text-slate-400 font-normal">
              · Click any card for step-by-step remediation guide
            </span>
          )}
        </div>
      }
      actions={
        <div className="flex flex-wrap gap-1">
          {["critical", "high", "medium", "low"].map((s) =>
            counts[s] ? (
              <button
                key={s}
                onClick={() => setSeverity(severity === s ? "" : s)}
                className={`rounded-lg px-2 py-0.5 text-xs font-semibold transition-all ${
                  severity === s
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {`${s} ${counts[s]}`}
              </button>
            ) : null
          )}
        </div>
      }
    >
      {shown.length ? (
        <div className="space-y-3" data-testid="findings">
        {shown.map((f) => <FindingCard key={f.id} f={f} onGuide={onGuide} onFix={onFix} onDismiss={onDismiss} />)}
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          No open findings. Click "Scan repository" above to inspect code.
        </p>
      )}
    </Card>
  );
}
