"use client";

import { CheckSquare, FolderGit2, FolderKanban, Bug, Plus, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { Button, Empty, ErrorNote, inputClass, Spinner, useToast } from "../../components/ui";
import { ConfirmModal } from "../../components/ConfirmModal";
import { NewProject } from "./NewProject";
import { ProjectCard } from "./ProjectCard";
import { StatsRow } from "./StatsRow";
import { api } from "../../lib/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[] | null>(null);
  const [archived, setArchived] = useState(false);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [projectToRename, setProjectToRename] = useState<any>(null);
  const [projectToRemove, setProjectToRemove] = useState<any>(null);
  const toast = useToast();

  const load = useCallback(() => {
    api(`/projects?archived=${archived}`)
      .then(setProjects)
      .catch((e) => setError(`Cannot reach the backend: ${e.message}`));
  }, [archived]);

  useEffect(() => {
    load();
  }, [load]);

  const shown = (projects || []).filter((p) =>
    `${p.name} ${p.description}`.toLowerCase().includes(query.toLowerCase())
  );

  const setArchivedFlag = async (p: any, value: boolean) => {
    await api(`/projects/${p.id}`, { method: "PATCH", json: { archived: value } });
    load();
  };

  const rename = (p: any) => {
    setProjectToRename(p);
  };

  const remove = (p: any) => {
    setProjectToRemove(p);
  };

  const all = projects || [];
  const needing = all.filter((p) => p.pending > 0).length;
  const stats: [string, number, any, string, string][] = [
    ["Projects", all.length, FolderKanban, "/projects", "projects"],
    ["Need my approval", needing, CheckSquare, "/approvals", "need-approval"],
    ["Open findings", all.reduce((n, p) => n + p.findings, 0), Bug, "/findings", "findings"],
    ["Documents", all.reduce((n, p) => n + p.documents, 0), FolderGit2, "/documents", "documents"],
  ];

  return (
    <AppShell>
      {!archived && projects !== null && all.length > 0 && <StatsRow stats={stats} />}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold">{archived ? "Archived projects" : "Projects"}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <input
              aria-label="Search projects"
              className={`${inputClass} w-56 pl-8`}
              placeholder="Search projects"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <Button variant="secondary" onClick={() => setArchived(!archived)}>
            {archived ? "Show active" : "Show archived"}
          </Button>
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" /> New project
          </Button>
        </div>
      </div>

      <ErrorNote message={error} />
      {projects === null && !error && <Spinner />}
      {projects !== null && !shown.length && (
        <Empty
          title={
            query
              ? "No project matches"
              : archived
              ? "No archived projects"
              : "No projects yet"
          }
        >
          {!query &&
            !archived &&
            "Create a project, then connect a repository or start writing requirements."}
        </Empty>
      )}

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {shown.map((p) => (
          <ProjectCard key={p.id} p={p} archived={archived} onRename={() => rename(p)} onArchive={() => setArchivedFlag(p, !archived)} onRemove={() => remove(p)} />
        ))}
      </div>

      {creating && <NewProject onClose={() => setCreating(false)} onCreated={load} />}

      {/* Confirmation Modal for Renaming Project */}
      <ConfirmModal
        isOpen={!!projectToRename}
        title="Rename Project"
        description="Update the display name of this project."
        confirmText="Save Name"
        requirePromptInput
        promptPlaceholder="Enter new project name"
        promptDefaultValue={projectToRename?.name || ""}
        onConfirm={async (newName) => {
          if (newName?.trim() && newName.trim() !== projectToRename?.name) {
            await api(`/projects/${projectToRename.id}`, { method: "PATCH", json: { name: newName.trim() } });
            toast("Project renamed");
            load();
          }
        }}
        onClose={() => setProjectToRename(null)}
      />

      {/* Confirmation Modal for Deleting Project */}
      <ConfirmModal
        isOpen={!!projectToRemove}
        title="Delete Project Permanently"
        description={`This permanently deletes "${projectToRemove?.name}", its repository copy, documents, and audit ledger. To confirm, type "${projectToRemove?.name}" below.`}
        tone="danger"
        confirmText="Delete Project"
        requirePromptInput
        promptPlaceholder={`Type ${projectToRemove?.name} to confirm`}
        onConfirm={async (typed) => {
          if (typed?.trim() === projectToRemove?.name) {
            await api(`/projects/${projectToRemove.id}`, { method: "DELETE" });
            toast("Project deleted");
            load();
          } else {
            toast("Project name did not match", "error");
          }
        }}
        onClose={() => setProjectToRemove(null)}
      />
    </AppShell>
  );
}
