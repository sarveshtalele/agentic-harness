"use client";

import { UploadCloud } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button, Card, Field, inputClass } from "../../components/ui";
import { api, upload } from "../../lib/api";

export function Connect({ project, busy, act }: any) {
  const [url, setUrl] = useState("");
  const [ref, setRef] = useState("");
  const [connections, setConnections] = useState<any[]>([]);
  const [credential, setCredential] = useState("");
  const [repos, setRepos] = useState<any[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [folder, setFolder] = useState("");
  useEffect(() => {
    api("/connections").then((res) => setConnections(Array.isArray(res) ? res : [])).catch(() => setConnections([]));
  }, []);
  useEffect(() => {
    if (credential) api(`/connections/${credential}/repos`).then((res) => setRepos(Array.isArray(res) ? res : [])).catch(() => setRepos([]));
    else setRepos([]);
  }, [credential]);
  return (
    <div className="mt-3 grid gap-4 md:grid-cols-3">
      <Card title="From Git">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); act("git", () => api(`/projects/${project.id}/repo/git`, { json: { url, ref, credential_id: credential || null } })); }}>
          <Field label="Private repository access" hint="A saved token is sent only to the Git host, never stored in the clone.">
            <select aria-label="Connection" className={inputClass} value={credential} onChange={(e) => setCredential(e.target.value)}>
              <option value="">None (public repository)</option>
              {connections.map((c) => <option key={c.id} value={c.id}>{c.label} ({c.login})</option>)}
            </select>
          </Field>
          {!connections.length && <p className="text-xs text-slate-500">Add a token in <Link className="text-indigo-500 underline" href="/settings">Settings</Link> to reach private repositories.</p>}
          {repos.length > 0 && (
            <Field label="Your repositories">
              <select aria-label="Your repositories" className={inputClass} onChange={(e) => setUrl(e.target.value)} defaultValue="">
                <option value="" disabled>Pick a repository</option>
                {repos.map((r) => <option key={r.clone_url} value={r.clone_url}>{r.full_name}{r.private ? " (private)" : ""}</option>)}
              </select>
            </Field>
          )}
          <Field label="HTTPS URL or owner/repo"><input required name="git-url" className={inputClass} placeholder="https://github.com/owner/repo" value={url} onChange={(e) => setUrl(e.target.value)} /></Field>
          <Field label="Branch or tag (optional)"><input className={inputClass} value={ref} onChange={(e) => setRef(e.target.value)} /></Field>
          <Button type="submit" busy={busy === "git"}>{busy === "git" ? "Cloning and scanning" : "Clone and scan"}</Button>
        </form>
      </Card>
      <Card title="From ZIP">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); const form = new FormData(); form.append("file", file as File); act("zip", () => upload(`/projects/${project.id}/repo/zip`, form)); }}>
          <Field label="ZIP archive" hint="No repository host needed. Traversal paths, symlinks, and zip bombs are refused."><input required type="file" name="zip-file" accept=".zip" className={inputClass} onChange={(e) => setFile(e.target.files?.[0] || null)} /></Field>
          <Button type="submit" busy={busy === "zip"}><UploadCloud className="h-4 w-4" /> Upload and scan</Button>
        </form>
      </Card>
      <Card title="From a folder on this machine">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); act("local", () => api(`/projects/${project.id}/repo/local`, { json: { path: folder } })); }}>
          <Field label="Folder path" hint="Copied into the project. The original folder is not changed."><input required name="folder-path" className={inputClass} value={folder} onChange={(e) => setFolder(e.target.value)} /></Field>
          <Button type="submit" busy={busy === "local"}>Import and scan</Button>
        </form>
      </Card>
    </div>
  );
}
