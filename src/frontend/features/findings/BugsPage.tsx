"use client";

import { Radar, Wrench } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useProject } from "../../components/ProjectShell";
import { ModelPicker } from "../../components/ModelPicker";
import { Badge, Button, Card, Empty, ErrorNote, PageTitle } from "../../components/ui";
import { api } from "../../lib/api";
import { RunDocuments } from "../runs/RunDocuments";
import { RunList } from "../runs/RunList";
import { RunPanel } from "../runs/RunPanel";
import { usePersistedRunId } from "../runs/usePersistedRunId";
import { DiagnoseCard } from "./DiagnoseCard";
import { FindingsList } from "./FindingsList";
import { GuideModal } from "./GuideModal";
import { useFindings } from "./useFindings";

export function BugsPage() {
  const { project, refresh } = useProject();
  const [severity, setSeverity] = useState("");
  const [trace, setTrace] = useState("");
  const [error, setError] = useState("");
  const [model, setModel] = useState("");
  const [selectedBugGuide, setSelectedBugGuide] = useState<any | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);
  const [runId, setRunId] = usePersistedRunId(`project_${project.id}_bugs_runId`);
  const { findings, load } = useFindings(project.id, runId, setRunId);

  if (!project?.repo) {
    return (
      <Empty title="Bug Scan needs code">
        <p className="mb-3">Connect a repository or upload a ZIP so the scan has code to read.</p>
        <Link className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500" href={`/projects/${project?.id || ""}/repository`}>
          Connect a repository
        </Link>
      </Empty>
    );
  }

  const start = async (workflow: string, input: object) => {
    setError("");
    try {
      const res = await api(`/projects/${project.id}/runs`, { json: { workflow, input, model } });
      if (res?.id) setRunId(res.id);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const dismiss = async (id: string) => {
    await api(`/findings/${id}`, { method: "PATCH", json: { status: "dismissed" } });
    load();
  };

  const safeFindings = Array.isArray(findings) ? findings : [];
  const counts = safeFindings.reduce((all, f) => {
    if (f?.severity) all[f.severity] = (all[f.severity] || 0) + 1;
    return all;
  }, {} as Record<string, number>);
  const shown = safeFindings.filter((f) => f && (!severity || f.severity === severity));

  const fix = (f: any) => start("change", { kind: "bugfix", finding_id: f.id, title: `Fix ${f.title}`.slice(0, 60) });

  return (
    <div className="space-y-6">
      <PageTitle
        title="Bug Scan & Defect Remediation"
        subtitle="Static scanners and multi-agent AST inspection of repository sandbox files with step-by-step fix guides."
        actions={
          <div className="flex items-center gap-2">
            <ModelPicker value={model} onChange={setModel} compact />
            <Button onClick={() => start("bug_scan", {})}>
              <Radar className="h-4 w-4" /> Scan repository
            </Button>
            {safeFindings.length > 0 && (
              <Button
                variant="secondary"
                onClick={() => start("change", { kind: "bugfix", fix_all: true })}
                title="Fixes up to 15 of the most severe open findings on one branch"
              >
                <Wrench className="h-4 w-4" /> Fix all
              </Button>
            )}
          </div>
        }
      />

      <ErrorNote message={error} />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px] [&>*]:min-w-0">
        <div className="space-y-4">
          {runId && (
            <RunPanel
              runId={runId}
              projectId={project.id}
              onFinished={() => {
                load();
                refresh();
              }}
            />
          )}

          <FindingsList findings={safeFindings} counts={counts} severity={severity} setSeverity={setSeverity} shown={shown} onGuide={setSelectedBugGuide} onFix={fix} onDismiss={dismiss} />
        </div>

        {/* Right Sidebar: Error Diagnosis & Past Runs */}
        <div className="space-y-4">
          <DiagnoseCard trace={trace} setTrace={setTrace} onDiagnose={() => start("change", { kind: "diagnose", title: "Diagnose error", spec: `Diagnose and fix this failure:\n${trace}` })} />

          <RunDocuments projectId={project.id} runId={runId} />

          <Card title="Past Runs">
            <RunList
              projectId={project.id}
              workflow={["bug_scan", "change"]}
              activeId={runId}
              onPick={setRunId}
              refreshKey={runId}
            />
          </Card>
        </div>
      </div>

      {/* Interactive Modal: End-to-End Bug Fix Guide */}
      {selectedBugGuide && (
        <GuideModal finding={selectedBugGuide} copiedCode={copiedCode} setCopiedCode={setCopiedCode} onClose={() => setSelectedBugGuide(null)} onApply={() => { const f = selectedBugGuide; setSelectedBugGuide(null); fix(f); }} />
      )}
    </div>
  );
}
