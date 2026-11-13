import { useState } from "react";
import { Badge, Button, Card, ConfirmModal, ErrorNote, useToast } from "../../components/ui";
import { api, when } from "../../lib/api";
import { GrantsTable } from "./GrantsTable";
import { TryTool } from "./TryTool";
import { Grant, Server } from "./types";

export function ServerCard({ server, admin, grants, roles, onChange }: { server: Server; admin: boolean; grants: Grant[]; roles: string[]; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [trying, setTrying] = useState("");
  const toast = useToast();
  const connect = async () => {
    setBusy(true); setError("");
    try { await api(`/mcp/servers/${server.id}/connect`, { method: "POST" }); } catch (e: any) { setError(e.message); } finally { setBusy(false); onChange(); }
  };
  const signIn = async () => {  // an OAuth server: this person signs in at the provider, then comes back here (R4)
    setError("");
    try { window.location.href = (await api(`/mcp/servers/${server.id}/oauth/start`, { json: { return_to: "/mcp" } })).url; } catch (e: any) { setError(e.message); }
  };
  const remove = async () => {
    setBusy(true);
    try { await api(`/mcp/servers/${server.id}`, { method: "DELETE" }); toast("Server deleted"); setConfirm(false); onChange(); } catch (e: any) { setError(e.message); setConfirm(false); } finally { setBusy(false); }
  };
  return (
    <div data-testid="mcp-server-card"><Card title={<span className="flex items-center gap-2">{server.name} <span data-testid="mcp-status"><Badge tone={server.status === "connected" ? "emerald" : server.status === "error" ? "rose" : "slate"}>{server.status}</Badge></span></span>}
      actions={admin && <div className="flex gap-2">{server.auth === "oauth" && <Button variant="secondary" onClick={signIn}>Sign in</Button>}<Button data-testid="mcp-connect" variant="secondary" busy={busy} onClick={connect}>{busy ? "Connecting" : "Connect"}</Button><Button variant="danger" onClick={() => setConfirm(true)}>Delete</Button></div>}>
      <div className="space-y-2 text-xs text-slate-500">
        <p className="mono">{server.transport} {server.transport === "stdio" ? [server.command, ...server.args].join(" ") : server.url}</p>
        {server.auth === "oauth" && <p>Each member signs in with OAuth. Sign in, then Connect to list the tools with your own sign-in.</p>}
        {server.secret_names.length > 0 && <p>Secrets set: {server.secret_names.join(", ")} (values are never shown)</p>}
        {server.plugin_id && <p>From plugin {server.plugin_id}</p>}
        <p>Last connected: {when(server.last_connected_at) || "never"}. Tools listed: {when(server.tools_listed_at) || "never"}.</p>
        <ErrorNote message={server.status === "error" ? server.error_message : null} />
        <ErrorNote message={error} />
        {server.status === "connected" && server.tools.length === 0 && <p>Connected, and the server lists no tools.</p>}
        {server.tools.map((t) => (
          <div key={t.name} data-testid="mcp-tool-row" className="rounded-lg border border-slate-200 p-2 dark:border-slate-800">
            <div className="flex items-center justify-between gap-2"><div><p className="mono text-sm text-slate-900 dark:text-slate-100">{t.name}</p><p>{t.description}</p></div>
              <Button variant="secondary" onClick={() => setTrying(trying === t.name ? "" : t.name)}>Try tool</Button></div>
            {trying === t.name && <TryTool server={server} tool={t} />}
          </div>
        ))}
        {admin && <GrantsTable server={server} grants={grants} roles={roles} onChange={onChange} />}
      </div>
      <ConfirmModal open={confirm} title="Delete MCP server" message={`Delete ${server.name}? Its grants and stored secrets go with it.`} confirmLabel="Delete" busy={busy} onConfirm={remove} onCancel={() => setConfirm(false)} />
    </Card></div>
  );
}
