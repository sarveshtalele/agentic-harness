import { useState } from "react";
import { Badge, Button, ErrorNote, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { PluginGrants } from "./PluginGrants";

export function PluginCard({ plugin, admin, onChange }: { plugin: any; admin: boolean; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();
  const act = async (path: string, done: (r: any) => string) => {
    setBusy(true); setError("");
    try { toast(done(await api(`/plugins/${plugin.id}/${path}`, { method: "POST" }))); onChange(); } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  const problems: string[] = [...plugin.problems, ...plugin.skill_problems];
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800" data-testid="plugin-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold">{plugin.id} <span className="text-xs font-normal text-slate-500">v{plugin.version}</span> <Badge tone={plugin.enabled ? "emerald" : "slate"}>{plugin.enabled ? "enabled" : "disabled"}</Badge> <Badge>{plugin.trust}</Badge></p>
        {admin && (
          <div className="flex gap-2">
            {plugin.mcp_servers.length > 0 && <Button variant="secondary" busy={busy} onClick={() => act("mcp/register", (r) => `Registered ${r.registered.length}, skipped ${r.skipped.length}, refused ${r.refused.length}`)}>Register MCP servers</Button>}
            <Button data-testid="plugin-toggle" variant={plugin.enabled ? "secondary" : "primary"} busy={busy} onClick={() => act(plugin.enabled ? "disable" : "enable", () => `Plugin ${plugin.enabled ? "disabled" : "enabled"}`)}>{plugin.enabled ? "Disable" : "Enable"}</Button>
          </div>
        )}
      </div>
      <p className="text-xs text-slate-500">{plugin.description}</p>
      <p className="text-xs text-slate-500">{plugin.skills} skills, {plugin.commands.length} commands, {plugin.mcp_servers.length} MCP servers. Source: {plugin.source}</p>
      <PluginGrants pluginId={plugin.id} admin={admin} />
      {problems.length > 0 && <ErrorNote message={problems.join("; ")} />}
      <ErrorNote message={error} />
    </div>
  );
}
