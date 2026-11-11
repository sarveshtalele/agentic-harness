import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Card, ErrorNote, useToast } from "../../components/ui";
import { useAuth } from "../../components/AuthGate";
import { api, upload } from "../../lib/api";
import { PluginCard } from "./PluginCard";

/** Installed plugins and their plugin grants. Admins upload a zip, switch plugins on or off and grant roles; everyone sees the list. */
export function PluginsCard() {
  const admin = useAuth().user?.role === "admin";
  const [plugins, setPlugins] = useState<any[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const load = useCallback(() => api("/plugins").then((r) => { setPlugins(r); setError(""); }).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const send = async (f?: File) => {
    if (!f) return;
    const form = new FormData(); form.append("file", f);
    setBusy(true); setError("");
    try { const p = await upload("/plugins/upload", form); toast(`Installed ${p.id}`); load(); } catch (e: any) { setError(e.message); } finally { setBusy(false); if (file.current) file.current.value = ""; }
  };
  return (
    <Card title="Plugins and plugin grants" actions={admin && <><input ref={file} type="file" accept=".zip" hidden data-testid="plugin-upload" onChange={(e) => send(e.target.files?.[0])} /><Button variant="secondary" busy={busy} onClick={() => file.current?.click()}>Upload plugin zip</Button></>}>
      <div className="space-y-2">
        {plugins?.length === 0 && <p className="text-sm text-slate-500">No plugins installed.</p>}
        {plugins?.map((p) => <PluginCard key={p.id} plugin={p} admin={admin} onChange={load} />)}
        <ErrorNote message={error} />
      </div>
    </Card>
  );
}
