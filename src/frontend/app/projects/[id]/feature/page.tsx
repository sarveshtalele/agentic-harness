"use client";

import { Hammer } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useProject } from "../../../../components/ProjectShell";
import { RunDocuments } from "../../../../features/runs/RunDocuments";
import { RunList } from "../../../../features/runs/RunList";
import { RunPanel } from "../../../../features/runs/RunPanel";
import { ModelPicker } from "../../../../components/ModelPicker";
import { Button, Card, Empty, ErrorNote, Field, inputClass, PageTitle } from "../../../../components/ui";
import { api } from "../../../../lib/api";

export default function FeaturePage() {
  const { project } = useProject();
  const [title, setTitle] = useState("");
  const [spec, setSpec] = useState("");
  const [install, setInstall] = useState(false);
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const RUN_STORAGE_KEY = `project_${project.id}_feature_runId`;
  const [runId, setRunIdState] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem(RUN_STORAGE_KEY) || null;
    }
    return null;
  });

  const setRunId = (id: string | null) => {
    setRunIdState(id);
    if (typeof window !== "undefined") {
      if (id) sessionStorage.setItem(RUN_STORAGE_KEY, id);
      else sessionStorage.removeItem(RUN_STORAGE_KEY);
    }
  };

  useEffect(() => {
    api(`/projects/${project.id}/runs`)
      .then((runs) => {
        if (Array.isArray(runs)) {
          const active = runs.find(
            (r: any) =>
              r?.workflow === "change" &&
              r?.input?.kind === "feature" &&
              ["running", "waiting_approval"].includes(r?.status)
          );
          if (active) setRunId(active.id);
        }
      })
      .catch(() => {});
  }, [project.id]);
  if (!project?.repo) return <Empty title="Feature Builder needs code"><Link className="text-indigo-500 underline" href={`/projects/${project?.id || ""}/repository`}>Connect a repository or upload a ZIP</Link></Empty>;
  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const run = await api(`/projects/${project.id}/runs`, { json: { workflow: "change", model, input: { kind: "feature", title, spec, install_deps: install } } });
      if (run?.id) setRunId(run.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageTitle title="Feature Builder" subtitle="The agent reads the repository, edits an isolated branch, and runs the real tests. You review the diff before anything is committed." />
      <div className="grid gap-4 lg:grid-cols-[1fr_300px] [&>*]:min-w-0">
        <div className="space-y-4">
          <Card title="Describe the change">
            <div className="space-y-3">
              <Field label="Title"><input name="feature-title" className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Add CSV export" /></Field>
              <Field label="Specification"><textarea name="feature-spec" rows={6} className={inputClass} value={spec} onChange={(e) => setSpec(e.target.value)} /></Field>
              <ModelPicker value={model} onChange={setModel} />
              <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={install} onChange={(e) => setInstall(e.target.checked)} /><span>Install repository dependencies before testing. <span className="text-amber-500">This runs the repository&apos;s install scripts on this machine.</span></span></label>
              <ErrorNote message={error} />
              <Button busy={busy} onClick={start} disabled={!title.trim() || !spec.trim()}><Hammer className="h-4 w-4" /> Build feature</Button>
            </div>
          </Card>
          {runId && <RunPanel runId={runId} projectId={project.id} />}
        </div>
        <div className="space-y-4"><RunDocuments projectId={project.id} runId={runId} /><Card title="Past runs"><RunList projectId={project.id} workflow={["change"]} activeId={runId} onPick={setRunId} refreshKey={runId} /></Card></div>
      </div>
    </>
  );
}
