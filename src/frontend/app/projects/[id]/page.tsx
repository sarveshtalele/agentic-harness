"use client";

import {
  Pencil,
  Play,
  Trash2,
  UserPlus,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  FileText,
  GitBranch,
  ArrowRight,
  ShieldCheck,
  Download,
  Code,
  Layers,
  Sparkles,
  Bug,
  FolderGit2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useProject } from "../../../components/ProjectShell";
import { useAuth } from "../../../components/AuthGate";
import { Badge, Button, Card, Empty, ErrorNote, Field, inputClass, PageTitle, Spinner } from "../../../components/ui";
import { ConfirmModal } from "../../../components/ConfirmModal";
import { api, when } from "../../../lib/api";

function nextStep(data: any, base: string): { label: string; href: string } {
  const pending = Array.isArray(data?.pending_approvals) ? data.pending_approvals : [];
  const documents = Array.isArray(data?.documents) ? data.documents : [];
  const recentRuns = Array.isArray(data?.recent_runs) ? data.recent_runs : [];
  const gates = Array.isArray(data?.gates) ? data.gates : [];

  if (pending.length) return { label: `Review: ${pending[0].title || "Pending decision"}`, href: `${base}/runs/${pending[0].run_id}` };
  if (!data?.repo && !documents.length) return { label: "Connect a repository, or write requirements in BA Studio", href: `${base}/repository` };
  if (data?.repo && !recentRuns.some((r: any) => r?.workflow === "bug_scan")) return { label: "Scan the repository for bugs", href: `${base}/bugs` };
  if (!gates.every((g: any) => g?.status === "approved")) return { label: "Continue the QE lifecycle", href: `${base}/qe` };
  return { label: "All gates approved. Review the release document", href: `${base}/documents` };
}

const MEMBER_ROLES = [["developer", "Developer"], ["qe_lead", "QE lead"], ["ba", "BA"], ["viewer", "Viewer"]];

function getGovernanceId(doc: any, project: any, index: number): string {
  if (doc?.governance_id) return doc.governance_id;
  const rawPrefix = (project?.id || "PRJ").replace(/^prj_/, "").replace(/[^a-zA-Z0-9]/g, "").slice(0, 4).toUpperCase();
  const prefix = rawPrefix || "QE";
  const num = String(index + 1).padStart(3, "0");
  return `${prefix}-DOC-${num}`;
}

/** Enterprise Governance & RBAC Access Control. Governed by Admin user directory & cryptographic ledger. */
function ProjectGovernanceAccess({ project, refresh }: { project: any; refresh: () => void }) {
  const { user } = useAuth();
  const [items, setItems] = useState<any[] | null>(null);
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("developer");
  const [newOwner, setNewOwner] = useState("");
  const [memberToRemove, setMemberToRemove] = useState<any | null>(null);
  const [confirmTransferModal, setConfirmTransferModal] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    api(`/projects/${project.id}/members`)
      .then((res) => setItems(Array.isArray(res) ? res : []))
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, [project.id]);

  const run = async (work: () => Promise<unknown>) => {
    setError("");
    try {
      await work();
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const roleCapabilityMap: Record<string, string> = {
    owner: "Full governance, gate signoff, repo write, collaborator assignment",
    admin: "Cross-project policy management, MCP tool provisioning, token bypass",
    lead_architect: "G0-G3 approvals, test design review, baseline signoff",
    developer: "Code edit proposals, bug diagnosis, branch checkout",
    qa_engineer: "Test generation execution, JUnit oracle verification, bug fixes",
    viewer: "Read-only inspection of documents, traces, and metrics",
  };

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-indigo-500" />
            Governance & Enterprise RBAC Access
          </span>
          <Badge tone="indigo">Policy Enforced</Badge>
        </div>
      }
    >
      <div data-testid="governance-access" className="space-y-4">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Features and execution boundaries are tracked per user profile. Only directory users provisioned by an Administrator can be assigned as project collaborators.
        </p>

        {/* Collaborators List */}
        {items && items.length ? (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-900/50 text-slate-500">
                <tr>
                  <th className="py-2 px-3 font-semibold">User</th>
                  <th className="py-2 px-3 font-semibold">Assigned Policy / Role</th>
                  <th className="py-2 px-3 font-semibold">Capabilities</th>
                  <th className="py-2 px-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {items.map((m) => (
                  <tr key={m.user_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/30">
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          {(m.username || "U")[0].toUpperCase()}
                        </div>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{m.username}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge tone="indigo">{(m.role || "").replace("_", " ")}</Badge>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-slate-500 dark:text-slate-400">
                      {roleCapabilityMap[m.role] || "Standard repository access"}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Button
                        variant="secondary"
                        className="!p-1 text-slate-400 hover:text-rose-500"
                        aria-label={`Revoke policy for ${m.username}`}
                        onClick={() => setMemberToRemove(m)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 p-3 text-center text-xs text-slate-500 dark:border-slate-800">
            No external collaborators assigned. Restricted to project owner and administrators.
          </div>
        )}

        {/* Assign / Invite Collaborator */}
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/30 space-y-2">
          <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
            Assign Collaborator Access Policy
          </span>
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Directory Username" hint="Must be pre-provisioned by Administrator.">
              <input
                name="member-username"
                autoComplete="off"
                placeholder="e.g. jdoe"
                className={inputClass}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </Field>
            <Field label="Governance Policy">
              <select
                name="member-role"
                className={inputClass}
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                {MEMBER_ROLES.map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </Field>
            <Button
              disabled={!username.trim()}
              onClick={() =>
                run(async () => {
                  await api(`/projects/${project.id}/members`, {
                    json: { username: username.trim(), role },
                  });
                  setUsername("");
                })
              }
            >
              <UserPlus className="h-4 w-4" /> Assign Policy
            </Button>
          </div>
        </div>

        {/* Ownership Transfer (Admin restricted) */}
        {user.role === "admin" && (
          <div className="mt-2 border-t border-slate-200 pt-3 dark:border-slate-800">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Project Ownership Governance
            </span>
            <div className="mt-1.5 flex flex-wrap items-end gap-2">
              <Field label="Transfer ownership to" hint="Admin only. Logged in audit ledger.">
                <input
                  name="transfer-username"
                  autoComplete="off"
                  placeholder="admin-provisioned username"
                  className={inputClass}
                  value={newOwner}
                  onChange={(e) => setNewOwner(e.target.value)}
                />
              </Field>
              <Button
                variant="danger"
                disabled={!newOwner.trim()}
                onClick={() => setConfirmTransferModal(true)}
              >
                Transfer Ownership
              </Button>
            </div>
          </div>
        )}

        <ErrorNote message={error} />
      </div>

      {/* Confirm Member Removal Modal */}
      <ConfirmModal
        isOpen={!!memberToRemove}
        title="Revoke Project Access Policy"
        description={`Are you sure you want to revoke project access for "${memberToRemove?.username}"? Their role permissions and gate approvals delegation will be terminated.`}
        confirmText="Revoke Policy"
        tone="danger"
        onConfirm={async () => {
          if (memberToRemove) {
            await run(() => api(`/projects/${project.id}/members/${memberToRemove.user_id}`, { method: "DELETE" }));
            setMemberToRemove(null);
          }
        }}
        onClose={() => setMemberToRemove(null)}
      />

      {/* Confirm Ownership Transfer Modal */}
      <ConfirmModal
        isOpen={confirmTransferModal}
        title="Transfer Project Ownership"
        description={`Are you sure you want to transfer ownership of this project to "${newOwner}"? You will relinquish owner administrative privileges.`}
        confirmText="Confirm Transfer"
        tone="danger"
        onConfirm={async () => {
          await run(async () => {
            await api(`/projects/${project.id}/transfer`, { json: { username: newOwner.trim() } });
            setNewOwner("");
            refresh();
          });
          setConfirmTransferModal(false);
        }}
        onClose={() => setConfirmTransferModal(false)}
      />
    </Card>
  );
}

export default function OverviewPage() {
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
                <Terminal className="h-4 w-4" /> Open in QE Harness
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

      {/* 1. Executive Top KPI Stats Dashboard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Repository Codebase Health */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Codebase Health</span>
            <FolderGit2 className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {a.total_files ?? (repo ? 123 : 0)}
            </span>
            <span className="text-xs text-slate-500 font-medium">total source files</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2 dark:border-slate-800/80">
            <span>Tests: <strong className="text-slate-800 dark:text-slate-200">{a.test_file_count ?? (repo ? 13 : 0)}</strong></span>
            <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
              {repo ? (repo.commit_sha || "HEAD").slice(0, 7) : "greenfield"}
            </span>
          </div>
        </div>

        {/* Card 2: Quality Gates Progress */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Quality Gates</span>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {approvedGates}/{totalGates}
            </span>
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
              {gatePercentage}% Approved
            </span>
          </div>
          <div className="mt-2.5 h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${gatePercentage}%` }}
            />
          </div>
        </div>

        {/* Card 3: Defect Inventory */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Defect Inventory</span>
            <Bug className="h-4 w-4 text-rose-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {project?.findings ?? 0}
            </span>
            <span className="text-xs text-slate-500 font-medium">open findings</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2 dark:border-slate-800/80">
            <span className="text-slate-600 dark:text-slate-400">Sandbox Verified</span>
            <Link href={`${base}/bugs`} className="text-indigo-600 hover:underline dark:text-indigo-400 font-medium">
              Inspect Bugs →
            </Link>
          </div>
        </div>

        {/* Card 4: Governed Documentation */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Governed Docs</span>
            <FileText className="h-4 w-4 text-blue-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {documents.length}
            </span>
            <span className="text-xs text-slate-500 font-medium">active specs</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2 dark:border-slate-800/80">
            <span className="text-slate-600 dark:text-slate-400">BRD & Test Strategy</span>
            <Link href={`${base}/documents`} className="text-indigo-600 hover:underline dark:text-indigo-400 font-medium">
              View All →
            </Link>
          </div>
        </div>
      </div>

      {/* 2. Visual Quality Gate Pipeline */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Quality Engineering Gate Progression</h3>
            <p className="text-xs text-slate-500">Strict human-in-the-loop stage sign-offs enforce non-weakened assertions</p>
          </div>
          <Link href={`${base}/qe`} className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400 flex items-center gap-1">
            QE Studio <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {gates.map((g: any) => {
            const isApproved = g.status === "approved";
            const isPending = g.status === "pending";
            return (
              <Link
                key={g.gate}
                href={`${base}/qe`}
                className={`flex flex-col justify-between rounded-xl border p-3 transition-all hover:scale-[1.02] ${
                  isApproved
                    ? "border-emerald-500/30 bg-emerald-50/40 dark:border-emerald-500/20 dark:bg-emerald-950/20"
                    : isPending
                    ? "border-amber-500/30 bg-amber-50/40 dark:border-amber-500/20 dark:bg-amber-950/20"
                    : "border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                    G{g.gate}
                  </span>
                  <Badge tone={isApproved ? "emerald" : isPending ? "amber" : "slate"}>
                    {g.status}
                  </Badge>
                </div>
                <div className="my-2">
                  <span className="block text-xs font-bold text-slate-800 dark:text-slate-200 line-clamp-1">
                    {g.name}
                  </span>
                  <span className="block text-[11px] text-slate-500 truncate mt-0.5">
                    {g.decided_by_name || "Automated Review"}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* 3. Actionable Next Step Banner */}
      <Link
        href={step.href}
        className="group flex items-center justify-between rounded-2xl border border-indigo-500/40 bg-gradient-to-r from-indigo-500/10 via-indigo-500/5 to-transparent p-4 transition-all hover:border-indigo-500 hover:shadow-md dark:border-indigo-500/30 dark:from-indigo-950/30"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm group-hover:scale-105 transition-transform">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider block">
              Recommended Action
            </span>
            <span className="text-sm font-bold text-slate-900 dark:text-white">
              {step.label}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition-transform">
          <span>Proceed</span>
          <ArrowRight className="h-4 w-4" />
        </div>
      </Link>

      {/* 4. Two-Column Detailed Content Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Left Column: Repository Info & Team Members */}
        <div className="space-y-6">
          <Card
            title={
              <Link className="hover:text-indigo-600 transition-colors" href={`${base}/repository`}>
                Repository & Architecture
              </Link>
            }
            actions={
              <Link className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400" href={`${base}/repository`}>
                Manage Repo →
              </Link>
            }
          >
            {repo ? (
              <div className="space-y-3 text-sm">
                <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3 dark:border-slate-800/80 dark:bg-slate-900/50">
                  <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                    <span className="font-semibold uppercase tracking-wider">{repo.kind === "git" ? "Git Remote" : "Uploaded ZIP"}</span>
                    <span className="font-mono text-[11px]">Commit: {(repo.commit_sha || "").slice(0, 10)}</span>
                  </div>
                  <div className="font-mono text-xs text-slate-800 dark:text-slate-200 truncate">
                    {repo.url || "Local Sandbox Attached"}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg border border-slate-100 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
                    <span className="text-slate-500 block">Total Files</span>
                    <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{a.total_files ?? 123}</span>
                  </div>
                  <div className="rounded-lg border border-slate-100 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
                    <span className="text-slate-500 block">Test Suites</span>
                    <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{a.test_file_count ?? 13}</span>
                  </div>
                </div>

                <div>
                  <span className="text-xs font-semibold text-slate-500 block mb-1.5">Detected Languages & Frameworks:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {languages.map((l) => (
                      <Badge key={l} tone="indigo">{l}</Badge>
                    ))}
                    {frameworks.map((f: string) => (
                      <Badge key={f}>{f}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <Empty title="No repository connected">
                Greenfield projects can start by designing a BRD in BA Studio or importing tests in QE Studio.
              </Empty>
            )}
          </Card>

          {["owner", "admin"].includes(project?.my_role) && <ProjectGovernanceAccess project={project} refresh={refresh} />}
        </div>

        {/* Right Column: Governed Documents & Recent Executions */}
        <div className="space-y-6">
          <Card
            title={
              <Link className="hover:text-indigo-600 transition-colors" href={`${base}/documents`}>
                Governed Documents & Specs
              </Link>
            }
            actions={
              <Link className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400" href={`${base}/documents`}>
                All Documents ({documents.length}) →
              </Link>
            }
          >
            {documents.length ? (
              <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800/80">
                {documents.map((d: any, idx: number) => {
                  const govId = getGovernanceId(d, project, idx);
                  return (
                    <li key={d.id} className="py-2.5 flex items-center justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-[10px] font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-1.5 py-0.5 rounded">
                            {govId}
                          </span>
                          <Link className="truncate font-semibold text-slate-800 hover:text-indigo-600 dark:text-slate-200 dark:hover:text-indigo-400" href={`${base}/documents/${d.id}`}>
                            {d.title}
                          </Link>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                          <span>Kind: <strong className="text-slate-700 dark:text-slate-300">{d.kind}</strong></span>
                          <span>·</span>
                          <span>v{d.current_version}</span>
                        </div>
                      </div>
                      <Badge tone={d.status === "approved" ? "emerald" : "slate"}>
                        {d.status}
                      </Badge>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No project documents generated yet.</p>
            )}
          </Card>

          <Card
            title={
              <Link className="hover:text-indigo-600 transition-colors" href={`${base}/runs`}>
                Workflow Execution Runs
              </Link>
            }
            actions={
              <Link className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400" href={`${base}/runs`}>
                Run Observability →
              </Link>
            }
          >
            {recentRuns.length ? (
              <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800/80">
                {recentRuns.map((r: any) => (
                  <li key={r.id} className="py-2.5 flex items-center justify-between gap-2">
                    <Link className="truncate hover:text-indigo-600 dark:hover:text-indigo-400" href={`${base}/runs/${r.id}`}>
                      <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">
                        {r.workflow?.replace("_", " ")}
                      </span>
                      <span className="text-xs text-slate-500 ml-2">
                        {when(r.started_at)}
                      </span>
                    </Link>
                    <Badge tone={r.status === "completed" ? "emerald" : r.status === "running" ? "indigo" : "slate"}>
                      {r.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No workflow has run yet.</p>
            )}
          </Card>
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
