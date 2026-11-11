import { useEffect, useState } from "react";
import { Badge, Button, Card, Field, inputClass, Markdown } from "../../components/ui";
import { api } from "../../lib/api";
import { PlanRecord } from "./types";
import { CallStatus, useCall } from "./useCall";

type Run = { verdict: string; exit_code: number | null; passed: number; failed: number; errors: number; stdout_tail: string; stderr_tail: string };
type Sample = { output: string; tokens_in: number; tokens_out: number; prompt_ref: string; draft_sha256: string };
type Doc = { id: string; title: string };

export function TestStep({ record }: { record: PlanRecord }) {
  const [run, setRun] = useState<Run | null>(null);
  const [sample, setSample] = useState<Sample | null>(null);
  const [text, setText] = useState("");
  const [docId, setDocId] = useState("");
  const [docs, setDocs] = useState<Doc[]>([]);
  const tests = useCall();
  const trial = useCall();
  useEffect(() => { api(`/skill-studio/documents?project_id=${record.project_id}`).then((r) => setDocs(r.documents)).catch(() => setDocs([])); }, [record.project_id]);
  const runTests = () => tests.run("Running the skill's tests…", async () => setRun(await api(`/skill-studio/plans/${record.id}/test`, { json: { mode: "scripts" } })));
  const trySample = () => trial.run("Trying the skill on the sample…", async () =>
    setSample(await api(`/skill-studio/plans/${record.id}/test`, { json: { mode: "sample", ...(docId ? { document_id: docId } : { sample_text: text }) } })));
  return (
    <Card title="6. Test the skill">
      <div className="space-y-5">
        {record.kind === "scripts" && (
          <div className="space-y-2">
            <Button onClick={runTests} disabled={!!tests.busy} busy={!!tests.busy} data-testid="studio-run-tests">Run skill tests</Button>
            <CallStatus call={tests} />
            {run && (
              <div className="space-y-2 text-xs">
                <p className="flex items-center gap-2" data-testid="studio-test-verdict"><Badge>{run.verdict}</Badge><span>{run.passed} passed, {run.failed} failed, {run.errors} errors (exit code {String(run.exit_code)})</span></p>
                {run.stdout_tail && <pre className="max-h-60 overflow-auto rounded-lg bg-slate-100 p-2 dark:bg-slate-900">{run.stdout_tail}</pre>}
                {run.stderr_tail && <pre className="max-h-40 overflow-auto rounded-lg bg-slate-100 p-2 dark:bg-slate-900">{run.stderr_tail}</pre>}
              </div>
            )}
          </div>
        )}
        <div className="space-y-2">
          <Field label="Try on a project document">
            <select className={inputClass} value={docId} onChange={(e) => setDocId(e.target.value)} data-testid="studio-sample-document">
              <option value="">No document: use the text below</option>
              {docs.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
            </select>
          </Field>
          {!docId && <Field label="Sample text"><textarea className={`${inputClass} h-24`} value={text} onChange={(e) => setText(e.target.value)} data-testid="studio-sample-text" /></Field>}
          <Button variant="secondary" onClick={trySample} disabled={!!trial.busy || (!docId && !text.trim())} busy={!!trial.busy} data-testid="studio-try-sample">Try on sample</Button>
          <CallStatus call={trial} />
          {sample && (
            <div className="space-y-2">
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800" data-testid="studio-sample-output"><Markdown>{sample.output}</Markdown></div>
              <p className="text-xs text-slate-500">Tokens in {sample.tokens_in}, out {sample.tokens_out}. Prompt <span className="mono">{sample.prompt_ref}</span>.</p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
