import { useState } from "react";
import { Button, Card } from "../../components/ui";
import { api } from "../../lib/api";
import { ChecksList } from "./ChecksList";
import { Generated, PlanRecord } from "./types";
import { CallStatus, useCall } from "./useCall";

export function GenerateStep({ record, onRecord }: { record: PlanRecord; onRecord: (r: PlanRecord) => void }) {
  const [result, setResult] = useState<Generated | null>(null);
  const [open, setOpen] = useState("");
  const call = useCall();
  const generate = () => call.run("Creating the skill files…", async () => {
    const out: Generated = await api(`/skill-studio/plans/${record.id}/generate`, { method: "POST" });
    setResult(out); setOpen(out.files[0]?.path ?? "");
    onRecord(await api(`/skill-studio/plans/${record.id}`));
  });
  const checks = result?.checks ?? record.checks;
  const shown = result?.files.find((f) => f.path === open);
  return (
    <Card title="5. Generate the skill files">
      <div className="space-y-3">
        <Button onClick={generate} disabled={!!call.busy} busy={!!call.busy} data-testid="studio-generate">{record.status === "generated" ? "Generate again" : "Generate files"}</Button>
        <CallStatus call={call} />
        {record.status === "generated" && !result && <p className="text-xs text-slate-500">Files were generated earlier. Their text is shown only right after generating; the checks below come from the stored record.</p>}
        {result && (
          <div className="grid gap-3 md:grid-cols-[14rem_1fr]">
            <ul className="space-y-1">
              {result.files.map((f) => (
                <li key={f.path}><button type="button" data-testid={`studio-file-${f.path}`} onClick={() => setOpen(f.path)} className={`mono w-full truncate rounded px-2 py-1 text-left text-xs ${open === f.path ? "bg-indigo-500/15" : "hover:bg-slate-500/10"}`}>{f.path}</button></li>
              ))}
            </ul>
            <pre className="max-h-96 overflow-auto rounded-lg bg-slate-100 p-3 text-xs dark:bg-slate-900" data-testid="studio-file-content">{shown?.content}</pre>
          </div>
        )}
        {checks.length > 0 && <div className="space-y-2"><p className="text-xs font-bold">Checks{result ? `: ${result.summary.passed} of ${result.summary.total} passed` : ""}</p><ChecksList checks={checks} /></div>}
      </div>
    </Card>
  );
}
