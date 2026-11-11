"use client";

import { Box, RefreshCw, Unplug } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, inputClass } from "../../components/ui";
import { ConfirmModal } from "../../components/ConfirmModal";
import { api, when } from "../../lib/api";

export function Details({ repo, project, busy, act, setRepo, refresh }: any) {
  const a = repo?.analysis || {};
  const loc = (a?.lines_of_code && typeof a.lines_of_code === "object") ? a.lines_of_code : {};
  const total = Object.values(loc as Record<string, number>).reduce((x: number, y: any) => x + (Number(y) || 0), 0) || 1;
  const routes = Array.isArray(a?.routes) ? a.routes : [];
  const ci = Array.isArray(a?.ci) ? a.ci : [];
  const frameworks = Array.isArray(a?.frameworks) ? a.frameworks : [];
  const testRunners = Array.isArray(a?.test_runners) ? a.test_runners : [];
  const entrypoints = Array.isArray(a?.entrypoints) ? a.entrypoints : [];
  const totalFiles = a?.total_files ?? 0;
  const sourceFiles = a?.source_files ?? 0;
  const testFilesCount = a?.test_file_count ?? 0;
  const mode = a?.mode || "brownfield";
  const commitSha = (repo?.commit_sha || "").slice(0, 10);
  const log = Array.isArray(repo?.log) ? repo.log : [];

  const [tree, setTree] = useState<string[]>([]);
  const [path, setPath] = useState("");
  const [content, setContent] = useState("");
  const [filter, setFilter] = useState("");
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);
  useEffect(() => {
    api(`/projects/${project.id}/repo/tree`)
      .then((d) => setTree(Array.isArray(d?.files) ? d.files : []))
      .catch(() => setTree([]));
  }, [project.id, repo?.commit_sha, repo?.scanned_at]);
  const open = async (p: string) => {
    setPath(p);
    try {
      const res = await api(`/projects/${project.id}/repo/file?path=${encodeURIComponent(p)}`);
      setContent(typeof res === "string" ? res : typeof res === "object" ? JSON.stringify(res, null, 2) : String(res ?? ""));
    } catch (e: any) {
      setContent(`Error reading file: ${e?.message || e}`);
    }
  };
  const disconnect = async () => {
    await api(`/projects/${project.id}/repo`, { method: "DELETE" });
    setRepo(null);
    refresh();
  };

  const safeTree = Array.isArray(tree) ? tree : [];
  const filteredTree = safeTree.filter((f) => f && f.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="mt-4 space-y-4" data-testid="repo-details">
      <Card title={<span className="truncate">{repo?.url || "Repository"}</span>} actions={
        <div className="flex gap-2">
          {repo?.kind === "git" && <Button variant="secondary" busy={busy === "sync"} onClick={() => act("sync", () => api(`/projects/${project.id}/repo/resync`, { method: "POST" }))}><RefreshCw className="h-4 w-4" /> Re-sync</Button>}
          <Button variant="danger" onClick={() => setShowDisconnectModal(true)}><Unplug className="h-4 w-4" /> Disconnect</Button>
        </div>
      }>
        <p className="text-xs text-slate-500">
          <Badge tone="emerald">Connected</Badge>
          {commitSha ? <> Commit <span className="mono">{commitSha}</span></> : null}
          {repo?.scanned_at ? <> · scanned {when(repo.scanned_at)}</> : null}
          {mode ? <> · <Badge tone="indigo">{mode}</Badge></> : null}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-2 text-center md:grid-cols-5">
          {[["Files", totalFiles], ["Source files", sourceFiles], ["Test files", testFilesCount], ["Routes", routes.length], ["CI workflows", ci.length]].map(([k, v]) => (
            <div key={k as string} className="rounded-lg bg-slate-100 p-2 dark:bg-slate-900"><dd className="text-lg font-bold">{v}</dd><dt className="text-xs text-slate-500">{k}</dt></div>
          ))}
        </dl>
      </Card>
      {repo?.sandbox && (
        <Card title={<span className="flex items-center gap-2"><Box className="h-4 w-4 text-indigo-500" /> Project sandbox</span>}>
          <dl className="grid gap-x-6 gap-y-1 text-sm md:grid-cols-2" data-testid="sandbox">
            <div><dt className="inline font-semibold">Clone: </dt><dd className="inline">{repo.sandbox.complete_history ? `Complete, ${repo.sandbox.commits ?? 0} commits` : "Partial history. The next scan completes it"}</dd></div>
            <div><dt className="inline font-semibold">Worktrees for runs: </dt><dd className="inline">{repo.sandbox.run_worktrees ?? 0}</dd></div>
            <div><dt className="inline font-semibold">Python environment: </dt><dd className="inline">{repo.sandbox.python_environment ? "Created" : "Created when you install dependencies"}</dd></div>
            <div><dt className="inline font-semibold">Disk use: </dt><dd className="inline">{repo.sandbox.size_mb ?? 0} MB</dd></div>
            <div className="md:col-span-2"><dt className="inline font-semibold">Folder: </dt><dd className="mono inline break-all text-xs">{repo.sandbox.path || "—"}</dd></div>
          </dl>
          <p className="mt-2 text-xs text-slate-500">Scans read this clone, and each change or test run works on its own branch here. Your main checkout and other projects are not touched. Test code runs without this platform&apos;s secrets.</p>
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Languages (lines of code)">
          {Object.keys(loc).length > 0 ? (
            <ul className="space-y-1.5 text-xs">
              {Object.entries(loc as Record<string, number>).map(([lang, lines]) => {
                const count = Number(lines) || 0;
                return (
                  <li key={lang}>
                    <div className="flex justify-between"><span>{lang}</span><span>{count.toLocaleString()}</span></div>
                    <div className="h-1.5 rounded bg-slate-200 dark:bg-slate-800">
                      <div className="h-1.5 rounded bg-indigo-500" style={{ width: `${Math.min(100, Math.max(0, (100 * count) / total))}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">No language statistics detected.</p>
          )}
        </Card>
        <Card title="Stack">
          <p className="text-sm"><b>Frameworks:</b> {frameworks.join(", ") || "none detected"}</p>
          <p className="text-sm"><b>Test runners:</b> {testRunners.join(", ") || "none detected"}</p>
          <p className="mt-2 text-sm font-semibold">Entry points</p>
          {entrypoints.length > 0 ? (
            <ul className="mono max-h-28 overflow-y-auto text-xs">{entrypoints.map((e: string) => <li key={e}>{e}</li>)}</ul>
          ) : (
            <p className="text-xs text-slate-500">none detected</p>
          )}
        </Card>
      </div>
      {routes.length > 0 && (
        <Card title="HTTP routes">
          <div className="max-h-56 overflow-auto"><table className="w-full text-left text-xs"><thead><tr><th>Method</th><th>Path</th><th>Location</th></tr></thead><tbody>
            {routes.map((r: any, i: number) => <tr key={i} className="border-t border-slate-200 dark:border-slate-800"><td className="py-0.5 font-semibold">{r?.method || "GET"}</td><td className="mono">{r?.path || "/"}</td><td className="mono text-slate-500">{r?.file || "—"}:{r?.line ?? 0}</td></tr>)}
          </tbody></table></div>
        </Card>
      )}
      <Card title={`Files (${safeTree.length})`}>
        <div className="grid gap-3 md:grid-cols-[280px_1fr] [&>*]:min-w-0">
          <div>
            <input aria-label="Filter files" className={`${inputClass} mb-2`} placeholder="Filter files" value={filter} onChange={(e) => setFilter(e.target.value)} />
            <ul className="mono max-h-96 overflow-y-auto text-xs">
              {filteredTree.slice(0, 500).map((f) => <li key={f}><button onClick={() => open(f)} className={`block w-full truncate px-1 text-left hover:bg-slate-100 dark:hover:bg-slate-900 ${path === f ? "text-indigo-500" : ""}`} title={f}>{f}</button></li>)}
              {filteredTree.length === 0 && <li className="px-1 text-slate-500">No files found.</li>}
            </ul>
          </div>
          <pre className="mono max-h-[28rem] min-h-40 overflow-auto rounded-lg bg-slate-100 p-3 text-xs dark:bg-[#070d1f]">{path ? content : "Select a file to read it."}</pre>
        </div>
      </Card>
      {log.length > 0 && (
        <Card title="Recent commits"><ul className="space-y-0.5 text-xs">{log.map((c: any) => <li key={c.sha || c.subject}><span className="mono text-slate-500">{(c.sha || "").slice(0, 10)}</span> {c.subject} <span className="text-slate-500">({c.author}, {c.date})</span></li>)}</ul></Card>
      )}

      {/* Confirmation Modal for Disconnecting Repository */}
      <ConfirmModal
        isOpen={showDisconnectModal}
        title="Disconnect Repository"
        description="Remove the local copy of this repository from the project? The remote repository is not affected."
        tone="danger"
        confirmText="Disconnect"
        onConfirm={disconnect}
        onClose={() => setShowDisconnectModal(false)}
      />
    </div>
  );
}
