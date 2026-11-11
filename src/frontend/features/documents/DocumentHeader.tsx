import { ArrowLeft, Check, Download, Trash2 } from "lucide-react";
import Link from "next/link";
import { Badge, Button } from "../../components/ui";
import { getDocGovernanceId } from "./lib";

type Props = { doc: any; project: any; docId: string; formats: string[]; isGherkin: boolean; onApprove: () => void; onDelete: () => void };

export function DocumentHeader({ doc, project, docId, formats, isGherkin, onApprove, onDelete }: Props) {
  return (
    <>
      <Link href={`/projects/${project.id}/documents`} className="mb-2 inline-flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-500"><ArrowLeft className="h-3 w-3" /> Documents</Link>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 dark:bg-indigo-950/60 dark:border-indigo-800/60 dark:text-indigo-300 px-2.5 py-1 rounded-lg">
              {getDocGovernanceId(doc, project)}
            </span>
            <h1 className="text-xl font-bold">{doc.title}</h1>
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Badge tone="indigo">{doc.kind}</Badge> <span data-testid="doc-version">v{doc.version ?? doc.current_version ?? 1}</span> <Badge tone={doc.status === "approved" ? "emerald" : "amber"}>{doc.status}</Badge> by {doc.author_name}
            {doc.prompt_ref && <span className="mono">{doc.prompt_ref}</span>}
            <span className="mono text-[11px]" title={doc.sha256}>sha256 {(doc.sha256 || "").slice(0, 12)}</span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {formats.map((f) => <a key={f} href={`/api/documents/${docId}/export/${f}`} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs sm:text-sm font-semibold hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"><Download className="h-4 w-4" /> .{f}</a>)}
          {doc.status !== "approved" && <Button variant="success" onClick={onApprove}><Check className="h-4 w-4" /> Approve</Button>}
          <Button variant="danger" aria-label="Delete document" onClick={() => onDelete()}><Trash2 className="h-4 w-4" /></Button>
        </div>
      </div>
      {isGherkin && doc.gherkin && <p className="mb-2 text-xs" data-testid="gherkin-status">{doc.gherkin.valid ? <Badge tone="emerald">{`Valid Gherkin: ${doc.gherkin.scenarios} scenarios, ${doc.gherkin.steps} steps`}</Badge> : <Badge tone="rose">Invalid Gherkin</Badge>}</p>}
    </>
  );
}
