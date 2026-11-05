"use client";

import { Pencil, Play, Trash2, UserPlus, Terminal } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useProject } from "../../../components/ProjectShell";
import { useAuth } from "../../../components/AuthGate";
import { Badge, Button, Card, Empty, ErrorNote, Field, inputClass, PageTitle, Spinner } from "../../../components/ui";
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

/** Owner and admin only. The owner types an exact username: it is answered added or not found, and no user list is ever shown. */
function Members({ project, refresh }: { project: any; refresh: () => void }) {
  const { user } = useAuth();
  const [items, setItems] = useState<any[] | null>(null);
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("developer");
  const [newOwner, setNewOwner] = useState("");
  const [error, setError] = useState("");
  const load = () => api(`/projects/${project.id}/members`).then((res) => setItems(Array.isArray(res) ? res : [])).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [project.id]);
  const run = async (work: () => Promise<unknown>) => {
    setError("");
    try { await work(); await load(); } catch (e: any) { setError(e.message); }
  };
  return (
    <Card title="Members">
      <div data-testid="members">
        {items && items.length ? (
          <ul className="mb-2 space-y-1 text-sm">{items.map((m) => <li key={m.user_id} className="flex items-center justify-between gap-2"><span>{m.username} <Badge>{(m.role || "").replace("_", " ")}</Badge></span><Button variant="secondary" aria-label={`Remove ${m.username}`} onClick={() => run(() => api(`/projects/${project.id}/members/${m.user_id}`, { method: "DELETE" }))}><Trash2 className="h-4 w-4" /></Button></li>)}</ul>
        ) : <p className="mb-2 text-sm text-slate-500">No members. Only you can see this project.</p>}
        <div className="flex flex-wrap items-end gap-2">
          <Field label="Username" hint="The exact username."><input name="member-username" autoComplete="off" className={inputClass} value={username} onChange={(e) => setUsername(e.target.value)} /></Field>
          <Field label="Role in this project"><select name="member-role" className={inputClass} value={role} onChange={(e) => setRole(e.target.value)}>{MEMBER_ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Field>
          <Button disabled={!username.trim()} onClick={() => run(async () => { await api(`/projects/${project.id}/members`, { json: { username: username.trim(), role } }); setUsername(""); })}><UserPlus className="h-4 w-4" /> Add</Button>
        </div>
        {user.role === "admin" && (
          <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
            <Field label="Transfer ownership to" hint="Admin only. The previous owner loses access."><input name="transfer-username" autoComplete="off" className={inputClass} value={newOwner} onChange={(e) => setNewOwner(e.target.value)} /></Field>
            <Button variant="danger" disabled={!newOwner.trim()} onClick={() => run(async () => { await api(`/projects/${project.id}/transfer`, { json: { username: newOwner.trim() } }); setNewOwner(""); refresh(); })}>Transfer</Button>
          </div>
        )}
        <ErrorNote message={error} />
      </div>
    </Card>
  );
}

export default function OverviewPage() {
  const { project, refresh } = useProject();
  const [data, setData] = useState<any>(null);
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
  return (
    <>
      <PageTitle
        title={project?.name || "Project"}
        subtitle={project?.description}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={async () => {
                const name = prompt("Project name", project?.name)?.trim();
                if (name && name !== project?.name) {
                  await api(`/projects/${project.id}`, { method: "PATCH", json: { name } });
                  refresh();
                }
              }}
            >
              <Pencil className="h-4 w-4" /> Rename
            </Button>
          </div>
        }
      />

      <Link href={step.href} className="mb-4 block rounded-xl border border-indigo-500/50 bg-indigo-500/10 p-3 text-sm font-semibold text-indigo-700 hover:bg-indigo-500/15 dark:text-indigo-300">Next: {step.label}</Link>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title={<Link className="hover:text-indigo-500" href={`${base}/repository`}>Repository</Link>} actions={<Link className="text-xs text-indigo-500" href={`${base}/repository`}>Manage</Link>}>
          {repo ? (
            <dl className="space-y-1 text-sm">
              <div className="truncate"><b>{repo.kind === "git" ? "Git" : "ZIP"}:</b> {repo.url || "Connected"}</div>
              <div><b>Commit:</b> <span className="mono text-xs">{(repo.commit_sha || "").slice(0, 10)}</span></div>
              <div><b>Files:</b> {a.total_files ?? 0} · <b>Test files:</b> {a.test_file_count ?? 0}</div>
              <div className="flex flex-wrap gap-1">{languages.map((l) => <Badge key={l} tone="indigo">{l}</Badge>)}{frameworks.map((f: string) => <Badge key={f}>{f}</Badge>)}</div>
            </dl>
          ) : <Empty title="No repository connected">Greenfield projects can start from BA Studio.</Empty>}
        </Card>
        <Card title={<Link className="hover:text-indigo-500" href={`${base}/governance`}>Quality gates</Link>} actions={<Link className="text-xs text-indigo-500" href={`${base}/governance`}>Governance</Link>}>
          <ul className="space-y-1 text-sm">
            {gates.map((g: any) => (
              <li key={g.gate}><Link href={`${base}/qe`} className="flex items-center justify-between gap-2 rounded hover:text-indigo-500">
                <span>G{g.gate} {g.name}</span>
                <span className="flex items-center gap-2 text-xs text-slate-500">{g.decided_by_name}<Badge>{g.status}</Badge></span>
              </Link></li>
            ))}
          </ul>
        </Card>
        {["owner", "admin"].includes(project?.my_role) && <Members project={project} refresh={refresh} />}
        <Card title={<Link className="hover:text-indigo-500" href={`${base}/runs`}>Recent runs</Link>} actions={<Link className="text-xs text-indigo-500" href={`${base}/runs`}>All runs</Link>}>
          {recentRuns.length ? (
            <ul className="space-y-1 text-sm">
              {recentRuns.map((r: any) => (
                <li key={r.id} className="flex items-center justify-between gap-2"><Link className="truncate hover:underline" href={`${base}/runs/${r.id}`}>{r.workflow} · {when(r.started_at)}</Link><Badge>{r.status}</Badge></li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-500">No workflow has run yet.</p>}
        </Card>
        <Card title={<Link className="hover:text-indigo-500" href={`${base}/documents`}>Latest documents</Link>} actions={<Link className="text-xs text-indigo-500" href={`${base}/documents`}>All documents</Link>}>
          {documents.length ? (
            <ul className="space-y-1 text-sm">
              {documents.map((d: any) => (
                <li key={d.id} className="flex items-center justify-between gap-2"><Link className="truncate hover:underline" href={`${base}/documents/${d.id}`}>{d.title}</Link><span className="flex shrink-0 items-center gap-1 text-xs">{d.kind} v{d.current_version}<Badge>{d.status}</Badge></span></li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-500">No documents yet.</p>}
        </Card>
      </div>
    </>
  );
}
