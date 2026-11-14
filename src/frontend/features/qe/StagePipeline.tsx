import { Play } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ModelPicker } from "../../components/ModelPicker";
import { Badge, Button, Card, ErrorNote } from "../../components/ui";
import { STAGES } from "./lib";

type Props = { project: any; safeDocs: any[]; safeGates: any[]; model: string; setModel: (v: string) => void; mode: "brownfield" | "greenfield"; install: boolean; setInstall: (v: boolean) => void; error: string; onStart: () => void };

export function StagePipeline({ project, safeDocs, safeGates, model, setModel, mode, install, setInstall, error, onStart }: Props) {
  const [modelOk, setModelOk] = useState(true);
  return (
    <Card title="Stages and gates" className="mb-4" id="stages-and-gates">
      <ol className="flex flex-wrap gap-2">
        {STAGES.filter(([, gate]) => mode === "greenfield" || gate !== "G5-Exec").map(([name, gate, kind]) => {
          const matchingDocs = safeDocs.filter((d) => d?.kind === kind);
          const doc = matchingDocs.find((d) => d?.status === "approved") || matchingDocs[0];
          const record = safeGates.find((g) => `G${g?.gate}` === gate);
          const isDocApproved = doc?.status === "approved";
          const isApproved = record?.status === "approved" || (kind === "discovery" && isDocApproved) || isDocApproved;
          const isPending = !isApproved && (record?.status === "pending" || doc?.status === "draft");
          const statusLabel = isApproved ? "approved" : (isPending ? "pending" : (record?.status || (doc ? doc.status : "pending")));

          const body = (
            <span
              className={`block rounded-xl border px-3 py-2 text-xs transition-all ${
                isApproved
                  ? "border-emerald-500/40 bg-emerald-50/60 dark:border-emerald-500/20 dark:bg-emerald-950/20"
                  : isPending
                  ? "border-amber-500/40 bg-amber-50/60 dark:border-amber-500/20 dark:bg-amber-950/20"
                  : "border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/40"
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-slate-200">
                <span>{name}</span>
                {gate && <span className="font-mono text-[10px] font-semibold text-slate-500 dark:text-slate-400">{gate}</span>}
                {gate && (
                  <Badge tone={statusLabel === "approved" ? "emerald" : statusLabel === "pending" ? "amber" : undefined}>
                    {statusLabel}
                  </Badge>
                )}
              </div>
              {doc && (
                <span className="mt-1 block font-mono text-[11px] text-indigo-600 dark:text-indigo-400">
                  doc v{doc.current_version}
                </span>
              )}
            </span>
          );

          return (
            <li key={name}>
              {doc ? (
                <Link href={`/projects/${project.id}/documents/${doc.id}`}>{body}</Link>
              ) : (
                body
              )}
            </li>
          );
        })}
      </ol>
      <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">Each stage ends at a gate (G0 to G5) that a named person signs. Pending means the stage waits for its document or its signature.</p>

      <div className="mt-4 flex flex-wrap items-center gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
        <Button onClick={onStart} disabled={!modelOk} title={modelOk ? undefined : "No model is allowed for your account"}>
          <Play className="h-4 w-4" /> Start the QE cycle
        </Button>
        <ModelPicker value={model} onChange={setModel} compact onAvailable={setModelOk} />
        {mode === "greenfield" && <label className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={install}
            onChange={(e) => setInstall(e.target.checked)}
            className="mt-0.5 rounded text-indigo-600"
          />
          <span>Install sandbox repository dependencies before running tests <span className="font-semibold text-amber-700 dark:text-amber-400">(runs install scripts)</span></span>
        </label>}
        {mode === "brownfield" && <span className="text-xs text-slate-500" data-testid="brownfield-note">Tests are not run here. You download them at Gate 5.</span>}
      </div>

      <ErrorNote message={error} />
    </Card>
  );
}
