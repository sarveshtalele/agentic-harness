"use client";

import { Play, Upload, Sparkles, FileText, CheckCircle2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useProject } from "../../../../components/ProjectShell";
import { RunDocuments, RunList, RunPanel } from "../../../../components/RunPanel";
import { ModelPicker } from "../../../../components/ModelPicker";
import { Badge, Button, Card, ErrorNote, Field, inputClass, PageTitle, useToast } from "../../../../components/ui";
import { api, upload } from "../../../../lib/api";

const DOMAIN_PRESETS = [
  {
    name: "ATM Machine",
    title: "ATM Cash Dispenser & Switch System Specification",
    brief: "Author an enterprise-grade Business Requirements Document (BRD) for an Automated Teller Machine (ATM) system with EMV chip card reader, encrypted PIN pad (3DES/AES), cash dispenser (multi-denomination cassettes), ISO-8583 banking switch messaging, offline failover, and strict cash retraction timeout.",
  },
  {
    name: "Payment Gateway",
    title: "Fintech Core Gateway & Settlement Engine",
    brief: "Author a comprehensive Business Requirements Document (BRD) for a PCI-DSS Level 1 compliant online payment gateway with idempotent checkout, double-entry ledger bookkeeping, 3D Secure 2.0 authentication, webhooks, and automated refund reconciliation.",
  },
  {
    name: "Calculator",
    title: "Python Calculator Full-Stack Application",
    brief: "Author a complete Business Requirements Document (BRD) for a high-precision Calculator application combining a React 18 frontend keypad with a Python AST backend supporting arbitrary decimal precision, history ledger, and zero eval() execution.",
  },
  {
    name: "Cloud Checkout",
    title: "Global E-Commerce Omnichannel Checkout",
    brief: "Author a Business Requirements Document (BRD) for an omnichannel shopping cart and checkout platform with real-time inventory reservation, multi-currency conversion, tax calculation, and fraud prevention scoring.",
  },
];

export default function BAPage() {
  const { project, refresh } = useProject();
  const [templates, setTemplates] = useState<any[]>([]);
  const [templateId, setTemplateId] = useState("builtin_brd");
  const [sources, setSources] = useState<any[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [brief, setBrief] = useState("");
  const [title, setTitle] = useState("");
  const [model, setModel] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();

  const loadTemplates = useCallback(() => api(`/templates?project_id=${project.id}`).then((res) => setTemplates(Array.isArray(res) ? res : [])).catch(() => setTemplates([])), [project.id]);
  const loadSources = useCallback(() => api(`/projects/${project.id}/sources`).then((res) => setSources(Array.isArray(res) ? res : [])).catch(() => setSources([])), [project.id]);
  const loadDocs = useCallback(() => api(`/projects/${project.id}/documents`).then((items) => setDocs(Array.isArray(items) ? items.filter((d: any) => ["brd", "prd", "stories", "gherkin"].includes(d?.kind)) : [])).catch(() => setDocs([])), [project.id]);
  
  useEffect(() => {
    loadTemplates();
    loadSources();
    loadDocs();
  }, [loadTemplates, loadSources, loadDocs]);

  // Documents refresh when a run is initiated or finished (strictly zero interval polling)
  useEffect(() => {
    if (!runId) return;
    loadDocs();
  }, [runId, loadDocs]);

  const safeDocs = Array.isArray(docs) ? docs : [];
  const safeTemplates = Array.isArray(templates) ? templates : [];
  const safeSources = Array.isArray(sources) ? sources : [];
  const recent = safeDocs.filter((d) => d && (d.run_id !== runId || !runId)).slice(0, 8);
  
  const getFileBadgeTone = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.endsWith(".pdf")) return "rose";
    if (lower.endsWith(".docx") || lower.endsWith(".doc")) return "indigo";
    if (lower.endsWith(".xlsx") || lower.endsWith(".csv")) return "emerald";
    return "slate";
  };

  const docLink = (d: any) => (
    <li key={d.id} className="flex items-center justify-between gap-2 p-1.5 rounded-lg border border-slate-100 bg-white hover:border-indigo-300 dark:border-slate-800 dark:bg-slate-900/60 transition">
      <div className="flex items-center gap-2 truncate">
        <FileText className="h-3.5 w-3.5 shrink-0 text-indigo-500" />
        <Link className="truncate text-xs font-semibold text-slate-800 hover:text-indigo-600 dark:text-slate-200 dark:hover:text-indigo-400" href={`/projects/${project.id}/documents/${d.id}`}>
          {d.title || "Untitled Document"}
        </Link>
      </div>
      <span className="flex shrink-0 items-center gap-1 text-[10px]">
        <Badge tone="indigo">{d.kind}</Badge>
        <span className="font-mono font-medium text-slate-500">v{d.current_version}</span>
        <Badge tone={d.status === "approved" ? "emerald" : "slate"}>{d.status}</Badge>
      </span>
    </li>
  );
  
  const template = safeTemplates.find((t) => t?.id === templateId);
  
  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const run = await api(`/projects/${project.id}/runs`, { json: { workflow: "ba", model, input: { brief, title: title || template?.name, template_id: templateId, source_ids: selected } } });
      setRunId(run.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  
  const addSource = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const source = await upload(`/projects/${project.id}/sources`, form);
      setSelected((s) => [...new Set([...s, source.id])]);
      loadSources();
      toast(source.duplicate ? "Already uploaded. Selected it." : `Extracted ${source.chars} characters`);
    } catch (e: any) {
      setError(e.message);
    }
  };
  
  const addTemplate = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("name", file.name.replace(/\.\w+$/, ""));
    form.append("project_id", project.id);
    try {
      const created = await upload("/templates/upload", form);
      await loadTemplates();
      setTemplateId(created.id);
      toast(`Template added with ${created?.headings?.length || 0} sections`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <>
      <PageTitle title="BA Studio" subtitle="Turn a brief and source documents into a domain-grounded 10-section requirements document and validated Gherkin scenarios." />
      
      {/* Autonomous Multi-Agent BA Lifecycle Flowchart */}
      <div className="mb-4 rounded-xl border border-indigo-100 bg-indigo-50/40 p-3 dark:border-indigo-900/40 dark:bg-indigo-950/20">
        <div className="mb-2 flex items-center justify-between text-xs font-semibold text-indigo-900 dark:text-indigo-200">
          <span className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
            Autonomous BA Lifecycle Pipeline (MAF 2.0)
          </span>
          <span className="font-mono text-[11px] text-indigo-600 dark:text-indigo-400">Gate 0 ➔ Gate 1 Continuous Verification</span>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-6 text-[11px]">
          <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">0</span>
            <span className="truncate font-medium">Gate 0: Scope</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">1</span>
            <span className="truncate font-medium">Context Ingest</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">2</span>
            <span className="truncate font-medium">Draft 10 Secs</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">3</span>
            <span className="truncate font-medium">Confidence Score</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-white/90 p-1.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900/80">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">4</span>
            <span className="truncate font-medium">Gherkin Oracles</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/80 p-1.5 shadow-2xs dark:border-emerald-800/60 dark:bg-emerald-950/40">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span className="truncate font-bold text-emerald-800 dark:text-emerald-300">Gate 1 Approved</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px] [&>*]:min-w-0">
        <div className="space-y-4">
          <Card title="New Requirements Specification">
            <div className="space-y-3">
              <div>
                <div className="mb-1.5 flex flex-wrap items-center justify-between gap-1 text-xs">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Project Brief</span>
                  <div className="flex flex-wrap items-center gap-1">
                    <span className="text-[10px] text-slate-400">Quick Presets:</span>
                    {DOMAIN_PRESETS.map((p) => (
                      <button
                        key={p.name}
                        type="button"
                        onClick={() => {
                          setBrief(p.brief);
                          setTitle(p.title);
                        }}
                        className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-700 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 transition"
                      >
                        {p.name}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  name="brief"
                  rows={5}
                  className={inputClass}
                  placeholder="What should be built, for whom, and why. Agents use only what you provide; unknowns become Open Questions."
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Document title">
                  <input
                    name="doc-title"
                    className={inputClass}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder={template?.name || "e.g., ATM Machine Business Requirements Document"}
                  />
                </Field>
                <Field label="Template format">
                  <select
                    aria-label="Template"
                    className={inputClass}
                    value={templateId}
                    onChange={(e) => setTemplateId(e.target.value)}
                  >
                    {safeTemplates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}{t.builtin ? "" : " (yours)"}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>

              {template && Array.isArray(template.headings) && template.headings.length > 0 && (
                <p className="text-xs text-slate-500">
                  <span className="font-semibold">Sections:</span> {template.headings.join(" · ")}
                </p>
              )}

              <label className="flex w-fit cursor-pointer items-center gap-1.5 text-xs font-semibold text-indigo-500 hover:underline">
                <Upload className="h-3.5 w-3.5" /> Upload your own template (.md, .docx)
                <input
                  type="file"
                  name="template-file"
                  accept=".md,.txt,.docx"
                  className="hidden"
                  onChange={(e) => addTemplate(e.target.files?.[0])}
                />
              </label>

              <ErrorNote message={error} />
              <ModelPicker value={model} onChange={setModel} compact />

              <Button onClick={start} busy={busy} disabled={!brief.trim() && !selected.length}>
                <Play className="h-4 w-4" /> Generate Requirements Document
              </Button>
            </div>
          </Card>

          {runId && (
            <RunPanel
              runId={runId}
              projectId={project.id}
              onFinished={() => {
                loadDocs();
                refresh();
              }}
            />
          )}
        </div>

        <div className="space-y-4">
          <RunDocuments projectId={project.id} runId={runId} />

          <Card title="Source documents">
            <label className="mb-2 inline-flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-indigo-500 hover:underline">
              <Upload className="h-3.5 w-3.5" /> Upload (.md, .txt, .pdf, .docx, .xlsx)
              <input
                type="file"
                name="source-file"
                accept=".md,.txt,.pdf,.docx,.xlsx,.pptx,.csv,.json,.yaml,.yml"
                className="hidden"
                onChange={(e) => addSource(e.target.files?.[0])}
              />
            </label>
            {safeSources.length ? (
              <ul className="space-y-1.5 text-xs">
                {safeSources.map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-1 rounded-lg border border-slate-100 bg-white p-1.5 dark:border-slate-800 dark:bg-slate-900/60">
                    <label className="flex items-center gap-2 truncate cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selected.includes(s.id)}
                        onChange={(e) =>
                          setSelected(e.target.checked ? [...selected, s.id] : selected.filter((x) => x !== s.id))
                        }
                      />
                      <span className="truncate font-medium text-slate-700 dark:text-slate-300" title={s.filename}>
                        {s.filename}
                      </span>
                    </label>
                    <Badge tone={getFileBadgeTone(s.filename)}>
                      {s.filename.split(".").pop()?.toUpperCase() || "FILE"}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">None uploaded.</p>
            )}
          </Card>

          <Card
            title="Recent documents"
            actions={
              <Link className="text-xs font-semibold text-indigo-500 hover:underline" href={`/projects/${project.id}/documents`}>
                All documents
              </Link>
            }
          >
            {recent.length ? (
              <ul className="space-y-1.5 text-sm" data-testid="recent-documents">
                {recent.map(docLink)}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">None yet.</p>
            )}
          </Card>

          <Card title="Past runs">
            <RunList
              projectId={project.id}
              workflow={["ba"]}
              activeId={runId}
              onPick={setRunId}
              refreshKey={runId}
            />
          </Card>
        </div>
      </div>
    </>
  );
}

