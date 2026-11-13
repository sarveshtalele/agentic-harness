import { useEffect, useState } from "react";
import { Button, Card, ErrorNote, inputClass, useToast } from "../../components/ui";
import { api } from "../../lib/api";

const ROLES = ["qe_lead", "ba", "developer", "viewer"];

/** Governance of features (R2, plan 12.3): role defaults, member overrides, and a member's effective access. Every save is ledgered. */
export function FeatureAccess() {
  const [data, setData] = useState<{ names: Record<string, string>; roles: Record<string, string[]>; overrides: Record<string, Record<string, boolean>> } | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [member, setMember] = useState("");
  const [effective, setEffective] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  const toast = useToast();
  const load = () => api("/features").then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); api("/users").then((u) => setUsers(u.filter((x: any) => x.id !== "admin"))).catch(() => {}); }, []);
  useEffect(() => { setEffective(null); if (member) api(`/features/effective/${member}`).then((r) => setEffective(r.features)).catch((e) => setError(e.message)); }, [member, data]);
  if (!data) return <Card title="Features"><ErrorNote message={error} /></Card>;
  const names = Object.keys(data.names);
  const nameOf = (id: string) => users.find((u) => u.id === id)?.username || id;
  const toggle = (role: string, feature: string, on: boolean) =>
    setData((d) => d && { ...d, roles: { ...d.roles, [role]: on ? [...(d.roles[role] || []), feature] : (d.roles[role] || []).filter((f) => f !== feature) } });
  const run = async (call: () => Promise<any>, done: string) => {
    setError("");
    try { await call(); toast(done); await load(); } catch (e: any) { setError(e.message); }
  };
  const save = () => run(() => api("/features/roles", { method: "PUT", json: Object.fromEntries(ROLES.map((r) => [r, data.roles[r] || []])) }), "Role defaults saved");
  const override = (feature: string, allowed: boolean | null) => run(() => api(`/features/overrides/${member}`, { method: "PUT", json: { feature, allowed } }), "Override saved");
  const mine = data.overrides[member] || {};

  return (
    <Card title="Features" actions={<Button variant="secondary" onClick={save}>Save role defaults</Button>}>
      <p className="mb-2 text-xs text-slate-500">Which parts of the platform each role may use. A member override wins over the role. Every change is written to the ledger with who, before and after. The admin has every feature.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" data-testid="feature-roles">
          <thead><tr><th>Role</th>{names.map((f) => <th key={f} className="px-1 text-xs">{data.names[f]}</th>)}</tr></thead>
          <tbody>{ROLES.map((role) => (
            <tr key={role}><td className="pr-2">{role.replace("_", " ")}</td>{names.map((f) => (
              <td key={f} className="px-1"><input type="checkbox" aria-label={`${role} may use ${data.names[f]}`} checked={(data.roles[role] || []).includes(f)} onChange={(e) => toggle(role, f, e.target.checked)} /></td>
            ))}</tr>
          ))}</tbody>
        </table>
      </div>
      <div className="mt-4 space-y-2">
        <label className="flex items-center gap-2 text-sm">Member
          <select aria-label="Member for overrides" className={`${inputClass} max-w-xs`} value={member} onChange={(e) => setMember(e.target.value)}>
            <option value="">Choose a member</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.username} ({u.account_role})</option>)}
          </select>
        </label>
        {member && (
          <div className="flex flex-wrap gap-2 text-xs" data-testid="feature-overrides">
            {names.map((f) => (
              <label key={f} className="flex items-center gap-1 rounded border border-slate-200 px-2 py-1 dark:border-slate-800">
                {data.names[f]}
                <select aria-label={`${data.names[f]} for ${nameOf(member)}`} className="bg-transparent" value={f in mine ? String(mine[f]) : ""}
                  onChange={(e) => override(f, e.target.value === "" ? null : e.target.value === "true")}>
                  <option value="">role default</option><option value="true">allow</option><option value="false">deny</option>
                </select>
              </label>
            ))}
          </div>
        )}
        {member && effective && <p className="text-sm" data-testid="feature-effective">Effective access for {nameOf(member)}: {effective.length ? effective.map((f) => data.names[f]).join(", ") : "none"}</p>}
        {Object.keys(data.overrides).length > 0 && <p className="text-xs text-slate-500">Members with overrides: {Object.keys(data.overrides).map(nameOf).join(", ")}</p>}
      </div>
      <ErrorNote message={error} />
    </Card>
  );
}
