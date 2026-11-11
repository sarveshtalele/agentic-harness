import { useCallback, useEffect, useState } from "react";
import { ErrorNote } from "../../components/ui";
import { api } from "../../lib/api";

type Grant = { id: string; role: string };

/** Which roles may use one plugin. No grant means every role may; the server enforces it. Admins toggle, others read. */
export function PluginGrants({ pluginId, admin }: { pluginId: string; admin: boolean }) {
  const [grants, setGrants] = useState<Grant[] | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api(`/plugins/${pluginId}/grants`).then((r) => { setGrants(r.grants); setRoles(r.roles); }).catch((e) => setError(e.message)), [pluginId]);
  useEffect(() => { load(); }, [load]);
  const toggle = async (role: string) => {
    const held = grants?.find((g) => g.role === role);
    setBusy(true); setError("");
    try {
      await (held ? api(`/plugins/${pluginId}/grants/${held.id}`, { method: "DELETE" }) : api(`/plugins/${pluginId}/grants`, { json: { role } }));
      await load();
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  if (grants === null) return <ErrorNote message={error} />;
  return (
    <div className="mt-2 space-y-1" data-testid="plugin-grants">
      <p className="text-xs font-semibold">Plugin grants</p>
      <p className="text-xs text-slate-500">{grants.length === 0 ? "No grants: every role may use this plugin." : "Only the ticked roles and the admin may use this plugin."}</p>
      <div className="flex flex-wrap gap-3">
        {roles.map((role) => (
          <label key={role} className="flex items-center gap-1 text-xs">
            <input type="checkbox" data-testid={`plugin-grant-${role}`} checked={grants.some((g) => g.role === role)} disabled={!admin || busy} onChange={() => toggle(role)} />
            {role}
          </label>
        ))}
      </div>
      <ErrorNote message={error} />
    </div>
  );
}
