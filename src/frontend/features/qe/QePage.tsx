"use client";

import { Download } from "lucide-react";
import { useState } from "react";
import { useProject } from "../../components/ProjectShell";
import { Button, Card, PageTitle } from "../../components/ui";
import { api } from "../../lib/api";
import { RunDocuments } from "../runs/RunDocuments";
import { RunList } from "../runs/RunList";
import { RunPanel } from "../runs/RunPanel";
import { usePersistedRunId } from "../runs/usePersistedRunId";
import { ModeSelector } from "./ModeSelector";
import { SandboxStatus } from "./SandboxStatus";
import { TraceView } from "./TraceView";
import { SetupPackageCard } from "./SetupPackageCard";
import { StagePipeline } from "./StagePipeline";
import { useActiveRun, useQeDocs } from "./useQeData";

export function QePage() {
  const { project, gates, refresh } = useProject();
  const [projectMode, setProjectMode] = useState<"brownfield" | "greenfield">("brownfield");
  const [install, setInstall] = useState(false);
  const [model, setModel] = useState("");
  const [error, setError] = useState("");
  const [runId, setRunId] = usePersistedRunId(`project_${project.id}_qe_runId`);
  const { docs, load } = useQeDocs(project.id, runId, setRunId);
  const activeRun = useActiveRun(runId);

  const start = async () => {
    setError("");
    try {
      const res = await api(`/projects/${project.id}/runs`, {
        json: { workflow: "qe", model, input: { mode: projectMode, ...(projectMode === "greenfield" ? { install_deps: install } : {}) } },
      });
      if (res?.id) setRunId(res.id);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const safeDocs = Array.isArray(docs) ? docs : [];
  const safeGates = Array.isArray(gates) ? gates : [];

  return (
    <div className="space-y-6">
      <PageTitle
        title="QE cycle"
        subtitle="From requirements to signed gates: plan, design, generate and run tests, each step approved by a person."
      />

      {/* Project Mode Selector (Greenfield vs Brownfield) */}
      <ModeSelector projectMode={projectMode} setProjectMode={setProjectMode} />

      <StagePipeline project={project} safeDocs={safeDocs} safeGates={safeGates} model={model} setModel={setModel} mode={projectMode} install={install} setInstall={setInstall} error={error} onStart={start} />

      <TraceView projectId={project.id} />

      <SetupPackageCard project={project} />

      {runId && <SandboxStatus project={project} runId={runId} activeRun={activeRun} />}

      {/* 4. Main Split View: Active Execution Panel & Past Runs */}
      <div className="grid gap-6 lg:grid-cols-[1fr_320px] [&>*]:min-w-0">
        <div>
          {runId ? (
            <RunPanel
              runId={runId}
              projectId={project.id}
              onFinished={() => {
                load();
                refresh();
              }}
            />
          ) : (
            <Card title="Current run">
              <p className="text-sm text-slate-500">
                No QE cycle run selected. Choose "Start the QE cycle" above, or pick a run from Past runs.
              </p>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <RunDocuments projectId={project.id} runId={runId} />
          <Card title="Past runs">
            <RunList
              projectId={project.id}
              workflow={["qe"]}
              activeId={runId}
              onPick={setRunId}
              refreshKey={runId}
            />
          </Card>
        </div>
      </div>
    </div>
  );
}
