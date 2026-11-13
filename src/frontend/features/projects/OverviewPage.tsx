"use client";

import { Pencil, Terminal } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useProject } from "../../components/ProjectShell";
import { Button, PageTitle, Spinner } from "../../components/ui";
import { ConfirmModal } from "../../components/ConfirmModal";
import { api } from "../../lib/api";
import { ProjectGovernanceAccess } from "./GovernanceAccess";
import { DocumentsCard } from "./DocumentsCard";
import { GatePipeline } from "./GatePipeline";
import { KpiCards } from "./KpiCards";
import { nextStep } from "./lib";
import { NextStepBanner } from "./NextStepBanner";
import { RepoCard } from "./RepoCard";
import { RunsCard } from "./RunsCard";

export function OverviewPage() {
  const { project, refresh } = useProject();
  const [data, setData] = useState<any>(null);
  const [showRenameModal, setShowRenameModal] = useState(false);

  useEffect(() => {
    api(`/projects/${project.id}/overview`).then(setData).catch(() => setData({}));
  }, [project.id]);

  if (!data) return <Spinner />;

  const base = `/projects/${project.id}`;
  const step = nextStep(data, base);
  const repo = data?.repo;
  const a = repo?.analysis || {};
  const languages = (a?.languages && typeof a.languages === "object") ? Object.keys(a.languages) : [];
  const frameworks = Array.isArray(a?.frameworks) ? a.frameworks : [];
  const gates = Array.isArray(data?.gates) ? data.gates : [];
  const recentRuns = Array.isArray(data?.recent_runs) ? data.recent_runs : [];
  const documents = Array.isArray(data?.documents) ? data.documents : [];
  const approvedGates = gates.filter((g: any) => g?.status === "approved").length;
  const totalGates = gates.length || 6;
  const gatePercentage = Math.round((approvedGates / totalGates) * 100);

  return (
    <div className="space-y-6">
      <PageTitle
        title={project?.name || "Project"}
        subtitle={project?.description || "Enterprise autonomous quality engineering platform"}
        actions={
          <div className="flex items-center gap-2">
            <Link href={`/harness?project=${project.id}`}>
              <Button variant="primary">
                <Terminal className="h-4 w-4" /> Open in the harness
              </Button>
            </Link>
            <Button
              variant="secondary"
              onClick={() => setShowRenameModal(true)}
            >
              <Pencil className="h-4 w-4" /> Rename
            </Button>
          </div>
        }
      />

      <KpiCards repo={repo} a={a} project={project} base={base} documents={documents} approvedGates={approvedGates} totalGates={totalGates} gatePercentage={gatePercentage} />

      <GatePipeline gates={gates} base={base} />

      <NextStepBanner step={step} />

      {/* 4. Two-Column Detailed Content Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-6">
          <RepoCard repo={repo} a={a} languages={languages} frameworks={frameworks} base={base} />

          {["owner", "admin"].includes(project?.my_role) && <ProjectGovernanceAccess project={project} refresh={refresh} />}
        </div>

        <div className="space-y-6">
          <DocumentsCard documents={documents} project={project} base={base} />

          <RunsCard recentRuns={recentRuns} base={base} />
        </div>
      </div>

      {/* Confirmation Modal for Project Renaming */}
      <ConfirmModal
        isOpen={showRenameModal}
        title="Rename Project"
        description="Update the display name of this project across all modules."
        confirmText="Save Name"
        requirePromptInput
        promptPlaceholder="Enter new project name"
        promptDefaultValue={project?.name || ""}
        onConfirm={async (newName) => {
          if (newName?.trim() && newName.trim() !== project?.name) {
            await api(`/projects/${project.id}`, { method: "PATCH", json: { name: newName.trim() } });
            refresh();
          }
        }}
        onClose={() => setShowRenameModal(false)}
      />
    </div>
  );
}
