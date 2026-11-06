"use client";

import { Plus, FileText, Download, ShieldCheck, ArrowRight, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useProject } from "../../../../components/ProjectShell";
import { Badge, Button, Card, Empty, ErrorNote, inputClass, PageTitle, Spinner } from "../../../../components/ui";
import { api, when } from "../../../../lib/api";

function getGovernanceId(doc: any, project: any, index: number): string {
  if (doc?.governance_id) return doc.governance_id;
  const rawPrefix = (project?.id || "PRJ").replace(/^prj_/, "").replace(/[^a-zA-Z0-9]/g, "").slice(0, 4).toUpperCase();
  const prefix = rawPrefix || "QE";
  const num = String(index + 1).padStart(3, "0");
  return `${prefix}-DOC-${num}`;
}

export default function DocumentsPage() {
  const { project } = useProject();
  const router = useRouter();
  const [docs, setDocs] = useState<any[] | null>(null);
  const [kind, setKind] = useState("");
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [template, setTemplate] = useState("builtin_brd");
  const [templates, setTemplates] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    // Strictly project-scoped document fetch
    api(`/projects/${project.id}/documents`)
      .then((res) => {
        const list = Array.isArray(res) ? res : [];
        // Strict project-id isolation safeguard
        const scoped = list.filter((d) => !d.project_id || d.project_id === project.id);
        setDocs(scoped);
      })
      .catch(() => setDocs([]));

    api(`/templates?project_id=${project.id}`)
      .then((res) => setTemplates(Array.isArray(res) ? res : []))
      .catch(() => setTemplates([]));
  }, [project.id]);

  const safeTemplates = Array.isArray(templates) ? templates : [];
  const create = async () => {
    try {
      const t = safeTemplates.find((x) => x?.id === template);
      const doc = await api(`/projects/${project.id}/documents`, {
        json: { title, kind: t?.kind || "brd", template_id: template },
      });
      router.push(`/projects/${project.id}/documents/${doc.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDownloadDoc = (doc: any) => {
    const content = doc.content || `# ${doc.title}\n\nGovernance ID: ${doc.id}\nKind: ${doc.kind}\nStatus: ${doc.status}\n`;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.title.replace(/[^a-zA-Z0-9_-]/g, "_")}_${doc.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!docs) return <Spinner />;
  const safeDocs = Array.isArray(docs) ? docs : [];
  const kinds = [...new Set(safeDocs.map((d) => d?.kind).filter(Boolean))];
  const shown = safeDocs.filter(
    (d) => d && (!kind || d.kind === kind) && (d.title || "").toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageTitle
        title="Governed Project Documents"
        subtitle="Versioned requirements, test plans, and release evidence isolated to this project with unique governance IDs."
      />

      <Card title="Author New Specification from Template" className="mb-4">
        <div className="flex flex-wrap items-center gap-2.5">
          <input
            aria-label="New document title"
            placeholder="e.g. Payments Reconciliation BRD"
            className={`${inputClass} max-w-sm`}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <select
            aria-label="Template for new document"
            className={`${inputClass} max-w-xs`}
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          >
            {safeTemplates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <Button onClick={create} disabled={!title.trim()}>
            <Plus className="h-4 w-4" /> Create Document
          </Button>
        </div>
        <ErrorNote message={error} />
      </Card>

      {safeDocs.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              aria-label="Search documents"
              className={`${inputClass} max-w-xs`}
              placeholder="Search by title..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <select
              aria-label="Filter by kind"
              className={`${inputClass} max-w-[180px]`}
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="">All Document Kinds</option>
              {kinds.map((k) => (
                <option key={k} value={k}>
                  {k.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            Showing {shown.length} of {safeDocs.length} project documents
          </span>
        </div>
      )}

      {shown.length ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:border-slate-800">
                <tr>
                  <th className="pb-3 pl-2">Governance ID</th>
                  <th className="pb-3">Title</th>
                  <th className="pb-3">Kind</th>
                  <th className="pb-3">Version</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Updated</th>
                  <th className="pb-3 pr-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {shown.map((d, idx) => {
                  const govId = getGovernanceId(d, project, idx);
                  return (
                    <tr key={d.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 pl-2 whitespace-nowrap">
                        <span className="rounded-md border border-indigo-200 bg-indigo-50 px-2 py-1 font-mono text-xs font-bold text-indigo-700 dark:border-indigo-800/60 dark:bg-indigo-950/60 dark:text-indigo-300">
                          {govId}
                        </span>
                      </td>
                      <td className="py-3 font-medium">
                        <Link
                          className="font-semibold text-slate-900 hover:text-indigo-600 dark:text-slate-100 dark:hover:text-indigo-400"
                          href={`/projects/${project.id}/documents/${d.id}`}
                        >
                          {d.title || "Untitled"}
                        </Link>
                      </td>
                      <td className="py-3 text-xs uppercase font-mono text-slate-600 dark:text-slate-400">
                        {d.kind}
                      </td>
                      <td className="py-3 text-xs font-mono">
                        v{d.current_version}
                      </td>
                      <td className="py-3">
                        <Badge tone={d.status === "approved" ? "emerald" : "slate"}>
                          {d.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-xs text-slate-500 whitespace-nowrap">
                        {when(d.updated_at)}
                      </td>
                      <td className="py-3 pr-2 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link href={`/projects/${project.id}/documents/${d.id}`}>
                            <Button variant="secondary" className="!px-2.5 !py-1 !text-xs">
                              Open Spec
                            </Button>
                          </Link>
                          <Button
                            variant="secondary"
                            className="!p-1 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400"
                            title="Download Markdown"
                            onClick={() => handleDownloadDoc(d)}
                          >
                            <Download className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Empty title="No documents found">
          Generate one in BA Studio or start from a template above.
        </Empty>
      )}
    </div>
  );
}
