import { useEffect, useState } from "react";
import { Button, Card, Empty, Field, inputClass } from "../../components/ui";
import { api, upload } from "../../lib/api";
import { Project, Source } from "./types";
import { CallStatus, useCall } from "./useCall";

type Doc = { id: string; title: string; kind: string; current_version: number };
type Parsed = { text: string; sha256: string; filename: string; chars: number };

export function SourceStep({ projects, projectId, onProject, onSource }: { projects: Project[]; projectId: string; onProject: (id: string) => void; onSource: (s: Source | null) => void }) {
  const [mode, setMode] = useState<Source["type"]>("document");
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [docId, setDocId] = useState("");
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<Parsed | null>(null);
  const call = useCall();
  const docsCall = useCall();
  useEffect(() => {
    setDocs(null); setDocId("");
    if (projectId) docsCall.run("Loading documents…", async () => setDocs((await api(`/skill-studio/documents?project_id=${projectId}`)).documents));
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (mode === "document") onSource(docId ? { type: "document", document_id: docId } : null);
    else if (mode === "upload") onSource(parsed ? { type: "upload", text: parsed.text, filename: parsed.filename } : null);
    else onSource(text.trim() ? { type: "text", text } : null);
  }, [mode, docId, parsed, text]); // eslint-disable-line react-hooks/exhaustive-deps
  const parse = (file?: File) => {
    if (!file) return;
    const form = new FormData(); form.append("file", file);
    call.run("Reading the source…", async () => setParsed(await upload("/skill-studio/sources/parse", form)));
  };
  return (
    <Card title="1. Project and source">
      <div className="space-y-3">
        <Field label="Project">
          <select className={inputClass} value={projectId} onChange={(e) => onProject(e.target.value)} data-testid="studio-project">
            <option value="">Choose a project</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
        {projects.length === 0 && <Empty title="No projects yet. Create a project first, then come back." />}
        {projectId && (
          <>
            <div className="flex gap-2">
              {([["document", "Project document"], ["upload", "Upload a file"], ["text", "Type requirements"]] as const).map(([m, label]) => (
                <Button key={m} variant={mode === m ? "primary" : "secondary"} onClick={() => setMode(m)} data-testid={`studio-source-${m}`}>{label}</Button>
              ))}
            </div>
            {mode === "document" && (docs && docs.length === 0
              ? <Empty title="This project has no documents you can see. Upload a file or type requirements instead." />
              : <Field label="Document"><select className={inputClass} value={docId} onChange={(e) => setDocId(e.target.value)} data-testid="studio-document">
                  <option value="">Choose a document</option>
                  {docs?.map((d) => <option key={d.id} value={d.id}>{d.title} ({d.kind}, v{d.current_version})</option>)}
                </select></Field>)}
            {mode === "upload" && (
              <div className="space-y-2">
                <input type="file" aria-label="Source file" data-testid="studio-source-file" disabled={!!call.busy} onChange={(e) => parse(e.target.files?.[0])} className="text-sm" />
                {parsed && <p className="text-xs text-slate-500" data-testid="studio-source-parsed">{parsed.filename}: {parsed.chars.toLocaleString()} characters, SHA-256 <span className="mono">{parsed.sha256}</span></p>}
              </div>
            )}
            {mode === "text" && <Field label="Requirements"><textarea className={`${inputClass} h-32`} value={text} onChange={(e) => setText(e.target.value)} data-testid="studio-source-input" placeholder="Paste or type the requirements the skill should be built from" /></Field>}
          </>
        )}
        <CallStatus call={call} /><CallStatus call={docsCall} />
      </div>
    </Card>
  );
}
