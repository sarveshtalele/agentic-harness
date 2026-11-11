"use client";

import { useState } from "react";
import { useProject } from "../../components/ProjectShell";
import { Card, PageTitle, useToast } from "../../components/ui";
import { api, upload } from "../../lib/api";
import { RunDocuments } from "../runs/RunDocuments";
import { RunList } from "../runs/RunList";
import { RunPanel } from "../runs/RunPanel";
import { LifecyclePipeline } from "./LifecyclePipeline";
import { getDomainPresets } from "./lib";
import { RecentDocs } from "./RecentDocs";
import { RequirementsForm } from "./RequirementsForm";
import { SourcesCard } from "./SourcesCard";
import { useBaData } from "./useBaData";

export function BaPage() {
  const { project, refresh } = useProject();
  const [templateId, setTemplateId] = useState("builtin_brd");
  const [selected, setSelected] = useState<string[]>([]);
  const [brief, setBrief] = useState("");
  const [title, setTitle] = useState("");
  const [model, setModel] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();
  const { templates, sources, docs, loadTemplates, loadSources, loadDocs } = useBaData(project.id, runId);

  const safeDocs = Array.isArray(docs) ? docs : [];
  const safeTemplates = Array.isArray(templates) ? templates : [];
  const safeSources = Array.isArray(sources) ? sources : [];
  const recent = safeDocs.filter((d) => d && (d.run_id !== runId || !runId)).slice(0, 8);

  const template = safeTemplates.find((t) => t?.id === templateId);
  const presets = getDomainPresets(project.name || "Project", project.repo?.url || "");
  
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
      <LifecyclePipeline />

      <div className="grid gap-4 lg:grid-cols-[1fr_320px] [&>*]:min-w-0">
        <div className="space-y-4">
          <RequirementsForm project={project} presets={presets} brief={brief} setBrief={setBrief} title={title} setTitle={setTitle} template={template} templateId={templateId} setTemplateId={setTemplateId} safeTemplates={safeTemplates} error={error} model={model} setModel={setModel} busy={busy} disabled={!brief.trim() && !selected.length} onStart={start} onTemplateFile={addTemplate} />

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

          <SourcesCard safeSources={safeSources} selected={selected} setSelected={setSelected} onUpload={addSource} />

          <RecentDocs recent={recent} projectId={project.id} />

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

