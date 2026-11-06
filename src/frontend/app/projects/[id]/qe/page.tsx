"use client";

import { Play, Download, Sparkles, FolderArchive, Terminal, ArrowRight, ShieldCheck, CheckCircle2, Sprout, Building2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useProject } from "../../../../components/ProjectShell";
import { RunDocuments, RunList, RunPanel } from "../../../../components/RunPanel";
import { ModelPicker } from "../../../../components/ModelPicker";
import { Badge, Button, Card, ErrorNote, PageTitle } from "../../../../components/ui";
import { api } from "../../../../lib/api";

const STAGES = [
  ["Intake", "G0", "intake"],
  ["Discovery", "AST", "discovery"],
  ["Requirements", "G1", "requirements"],
  ["Test plan", "G2", "test_plan"],
  ["Test design", "G3", "test_cases"],
  ["Generate", "G4", "test_code"],
  ["Execute & Heal", "G5-Exec", ""],
  ["Traceability", "Matrix", "traceability"],
  ["Release", "G5", "release"],
];

export default function QEPage() {
  const { project, gates, refresh } = useProject();
  const [projectMode, setProjectMode] = useState<"brownfield" | "greenfield">("brownfield");
  const [install, setInstall] = useState(false);
  const [model, setModel] = useState("");
  const [docs, setDocs] = useState<any[]>([]);
  const [error, setError] = useState("");

  // 1. Persistent Storage Memory Key: Persist active or latest run across tab switches
  const RUN_STORAGE_KEY = `project_${project.id}_qe_runId`;
  const [runId, setRunIdState] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(RUN_STORAGE_KEY) || sessionStorage.getItem(RUN_STORAGE_KEY) || null;
    }
    return null;
  });

  const setRunId = (id: string | null) => {
    setRunIdState(id);
    if (typeof window !== "undefined") {
      if (id) {
        localStorage.setItem(RUN_STORAGE_KEY, id);
        sessionStorage.setItem(RUN_STORAGE_KEY, id);
      } else {
        localStorage.removeItem(RUN_STORAGE_KEY);
        sessionStorage.removeItem(RUN_STORAGE_KEY);
      }
    }
  };

  const load = useCallback(() => {
    api(`/projects/${project.id}/documents`)
      .then((res) => {
        const list = Array.isArray(res) ? res : [];
        setDocs(list.filter((d) => !d.project_id || d.project_id === project.id));
      })
      .catch(() => setDocs([]));
  }, [project.id]);

  useEffect(() => {
    load();
    api(`/projects/${project.id}/runs`)
      .then((runs) => {
        if (Array.isArray(runs)) {
          const active = runs.find(
            (r: any) =>
              r?.workflow === "qe" &&
              ["running", "waiting_approval"].includes(r?.status)
          );
          if (active) {
            setRunId(active.id);
          } else if (!runId) {
            const latest = runs.find((r: any) => r?.workflow === "qe");
            if (latest) setRunId(latest.id);
          }
        }
      })
      .catch(() => {});
  }, [load, project.id]);

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
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xs dark:border-slate-800 dark:bg-[#0b1329]">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
            Lifecycle Strategy:
          </span>
          <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setProjectMode("brownfield")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                projectMode === "brownfield"
                  ? "bg-white text-indigo-700 shadow-sm dark:bg-indigo-950 dark:text-indigo-300 border border-slate-200 dark:border-indigo-800"
                  : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-300"
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              <span>Brownfield (Scan Existing Codebase & Evolve)</span>
            </button>
            <button
              type="button"
              onClick={() => setProjectMode("greenfield")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                projectMode === "greenfield"
                  ? "bg-white text-emerald-700 shadow-sm dark:bg-emerald-950 dark:text-emerald-300 border border-slate-200 dark:border-emerald-800"
                  : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-300"
              }`}
            >
              <Sprout className="h-3.5 w-3.5" />
              <span>Greenfield (Generate Complete App from BRD & Scratch)</span>
            </button>
          </div>
        </div>
        <span className="text-xs text-slate-500 font-medium">
          {projectMode === "brownfield" ? "AST & static analysis scans active repository sandbox" : "AI SDLC generates complete application modules, suites, and runners"}
        </span>
      </div>

      {/* 1. Autonomous AI SDLC Lifecycle Stage Tracker */}
      <Card title="Autonomous AI SDLC & Quality Gate Pipeline" className="mb-4">
        <ol className="flex flex-wrap gap-2">
          {STAGES.map(([name, gate, kind]) => {
            const matchingDocs = safeDocs.filter((d) => d?.kind === kind);
            const doc = matchingDocs.find((d) => d?.status === "approved") || matchingDocs[0];
            const record = safeGates.find((g) => `G${g?.gate}` === gate);
            const isDocApproved = doc?.status === "approved";
            const isApproved = record?.status === "approved" || (kind === "discovery" && isDocApproved) || isDocApproved;
            const isPending = !isApproved && (record?.status === "pending" || doc?.status === "draft");
            const statusLabel = isApproved ? "approved" : (isPending ? "pending" : (record?.status || (doc ? doc.status : "pending")));

            const body = (
              <span
                className={`block rounded-xl border px-3 py-2 text-xs transition-all ${
                  isApproved
                    ? "border-emerald-500/40 bg-emerald-50/60 dark:border-emerald-500/20 dark:bg-emerald-950/20"
                    : isPending
                    ? "border-amber-500/40 bg-amber-50/60 dark:border-amber-500/20 dark:bg-amber-950/20"
                    : "border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/40"
                }`}
              >
                <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-slate-200">
                  <span>{name}</span>
                  {gate && (
                    <Badge tone={isApproved ? "emerald" : isPending ? "amber" : "slate"}>
                      {statusLabel}
                    </Badge>
                  )}
                </div>
                {doc && (
                  <span className="mt-1 block font-mono text-[11px] text-indigo-600 dark:text-indigo-400">
                    doc v{doc.current_version}
                  </span>
                )}
              </span>
            );

            return (
              <li key={name}>
                {doc ? (
                  <Link href={`/projects/${project.id}/documents/${doc.id}`}>{body}</Link>
                ) : (
                  body
                )}
              </li>
            );
          })}
        </ol>

        <div className="mt-4 flex flex-wrap items-center gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
          <Button onClick={start}>
            <Play className="h-4 w-4" /> Start QE Lifecycle
          </Button>
          <ModelPicker value={model} onChange={setModel} compact />
          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={install}
              onChange={(e) => setInstall(e.target.checked)}
              className="rounded text-indigo-600"
            />
            <span>Install sandbox repository dependencies before running tests</span>
            <span className="text-amber-500 font-semibold">(runs install scripts)</span>
          </label>
        </div>

        <ErrorNote message={error} />
      </Card>

      {/* 2. Downloadable Setup Package Card */}
      <div className="rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50/50 via-slate-50/30 to-white p-4 shadow-sm dark:border-indigo-950/60 dark:from-indigo-950/20 dark:to-[#0b1329]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-md">
              <FolderArchive className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                One-Click Local Sandbox Execution Package
              </h3>
              <p className="text-xs text-slate-500">
                Includes application source code, deterministic test suites, <code>setup_mac_linux.sh</code>, and <code>setup_windows.bat</code>.
              </p>
            </div>
          </div>

          <a
            href={`/api/projects/${project.id}/export-zip`}
            download={`${project.id}_sdlc_export.zip`}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-colors"
          >
            <Download className="h-4 w-4" /> Download Setup Package (.ZIP)
          </a>
        </div>
      </div>

      {/* 3. Main Split View: Active Execution Panel & Past Runs */}
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
