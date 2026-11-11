import { useEffect, useState } from "react";
import { Button, Card, ErrorNote, useToast } from "../../components/ui";
import { api } from "../../lib/api";

const GATES = ["G0 Intake", "G1 Requirements", "G2 Plan", "G3 Design", "G4 Generate", "G5 Release"];

/** Which roles may sign each gate. A gate with nothing ticked can be signed by anyone who can write. The admin can always sign. */
export function GateRoles() {
  const [map, setMap] = useState<Record<string, string[]> | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const toast = useToast();
  useEffect(() => { api("/settings/gate-roles").then((r) => { setMap(r.roles); setRoles(r.assignable); }).catch((e) => setError(e.message)); }, []);
  if (!map) return <Card title="Who may sign each gate"><ErrorNote message={error} /></Card>;
  const toggle = (gate: number, role: string, on: boolean) => setMap((m) => ({ ...m, [gate]: on ? [...(m?.[gate] || []), role] : (m?.[gate] || []).filter((r) => r !== role) }));
  const save = async () => {
    setError("");
    try { const r = await api("/settings/gate-roles", { method: "PUT", json: { roles: map } }); setMap(r.roles); toast("Gate roles saved"); } catch (e: any) { setError(e.message); }
  };
  return (
    <Card title="Who may sign each gate" actions={<Button variant="secondary" onClick={save}>Save</Button>}>
      <p className="mb-2 text-xs text-slate-500">Tick the roles allowed to sign a gate. With none ticked, anyone who can write in the project may sign it. A project member needs the role on their account and in the project.</p>
      <table className="w-full text-left text-sm" data-testid="gate-roles">
        <thead><tr><th>Gate</th>{roles.map((r) => <th key={r} className="text-xs">{r.replace("_", " ")}</th>)}</tr></thead>
        <tbody>{GATES.map((name, gate) => <tr key={gate}><td>{name}</td>{roles.map((r) => <td key={r}><input type="checkbox" aria-label={`${r} may sign ${name}`} checked={(map[gate] || []).includes(r)} onChange={(e) => toggle(gate, r, e.target.checked)} /></td>)}</tr>)}</tbody>
      </table>
      <ErrorNote message={error} />
    </Card>
  );
}
