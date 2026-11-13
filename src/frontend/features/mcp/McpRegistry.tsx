import { useCallback, useEffect, useState } from "react";
import { Button, Card, Empty, ErrorNote, Spinner } from "../../components/ui";
import { useAuth } from "../../components/AuthGate";
import { api } from "../../lib/api";
import { Catalog } from "./Catalog";
import { ServerCard } from "./ServerCard";
import { ServerForm } from "./ServerForm";
import { Grant, Server, Template } from "./types";

export function McpRegistry() {
  const admin = useAuth().user?.role === "admin";
  const [data, setData] = useState<any>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [grants, setGrants] = useState<Grant[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [form, setForm] = useState<{ prefill: Template | null } | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setData(await api("/mcp/servers"));
      if (admin) { const g = await api("/mcp/grants"); setGrants(g.grants); setRoles(g.roles); }
      setError("");
    } catch (e: any) { setError(e.message); }
  }, [admin]);
  useEffect(() => { load(); api("/mcp/catalog").then((r) => setTemplates(r.templates)).catch((e) => setError(e.message)); }, [load]);
  if (!data) return error ? <ErrorNote message={error} /> : <Spinner />;
  const stats: [string, number][] = [["Servers", data.total_servers], ["Connected", data.connected_servers], ["Tools listed", data.total_tools], ["Tools granted", data.authorized_tools]];
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map(([label, n]) => <Card key={label}><p className="text-xs text-slate-500">{label}</p><p className="text-2xl font-bold" data-testid={`mcp-stat-${label.toLowerCase().replace(" ", "-")}`}>{n}</p></Card>)}
      </div>
      <ErrorNote message={error} />
      {!data.stdio_allowed && <p className="text-xs text-slate-500">stdio servers run only in local development; on the web use an HTTP or WebSocket server.</p>}
      {admin && !form && <Button onClick={() => setForm({ prefill: null })}>Add server</Button>}
      {admin && form && <ServerForm prefill={form.prefill} stdioAllowed={data.stdio_allowed} onCancel={() => setForm(null)} onAdded={() => { setForm(null); load(); }} />}
      {admin && <Catalog templates={templates} stdioAllowed={data.stdio_allowed} onPick={(t) => setForm({ prefill: t })} />}
      {data.servers.length === 0 && <Empty title="No MCP servers yet. Add one from the catalog or by hand." />}
      {data.servers.map((s: Server) => <ServerCard key={s.id} server={s} admin={admin} grants={grants.filter((g) => g.server_id === s.id)} roles={roles} onChange={load} />)}
    </div>
  );
}
