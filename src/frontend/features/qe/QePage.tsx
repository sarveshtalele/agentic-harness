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
        json: { workflow: "qe", model, input: { install_deps: install, mode: projectMode } },
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
        title="Autonomous QE & AI SDLC Lifecycle"
        subtitle="End-to-end quality engineering lifecycle from BRD intake to automated sandbox build, test generation, and setup ZIP package export."
        actions={
          <div className="flex items-center gap-2">
            <a
              href={`/api/projects/${project.id}/export-zip`}
              download={`${project.id}_sdlc_export.zip`}
            >
              <Button variant="secondary">
                <Download className="h-4 w-4" /> Export SDLC Package (.ZIP)
              </Button>
            </a>
          </div>
        }
      />

      {/* Project Mode Selector (Greenfield vs Brownfield) */}
      <ModeSelector projectMode={projectMode} setProjectMode={setProjectMode} />

      <StagePipeline project={project} safeDocs={safeDocs} safeGates={safeGates} model={model} setModel={setModel} install={install} setInstall={setInstall} error={error} onStart={start} />

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
            <Card title="Active Execution Run">
              <p className="text-sm text-slate-500">
                No active QE lifecycle run selected. Click "Start QE Lifecycle" above or pick a run from Past Runs.
              </p>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <RunDocuments projectId={project.id} runId={runId} />
          <Card title="Past QE Runs">
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
