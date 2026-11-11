import { useState } from "react";
import { Button, ErrorNote } from "../../components/ui";
import { api } from "../../lib/api";
import { Grant, Server } from "./types";

/** Which role may call which tool of one server. Admin only; the server enforces it. */
export function GrantsTable({ server, grants, roles, onChange }: { server: Server; grants: Grant[]; roles: string[]; onChange: () => void }) {
  const [tool, setTool] = useState("*");
  const [role, setRole] = useState("");
  const [error, setError] = useState("");
  const act = async (run: () => Promise<unknown>) => { setError(""); try { await run(); onChange(); } catch (e: any) { setError(e.message); } };
  return (
    <div className="space-y-2" data-testid="mcp-grants">
      <p className="text-xs font-semibold">Grants</p>
      {grants.length === 0 ? <p className="text-xs text-slate-500">No grants. No role can call these tools yet.</p> : (
        <table className="w-full text-left text-xs"><thead><tr><th>Tool</th><th>Role</th><th /></tr></thead><tbody>
          {grants.map((g) => (
            <tr key={g.id} data-testid="mcp-grant-row"><td className="mono">{g.tool_name}</td><td>{g.role}</td>
              <td><Button variant="danger" onClick={() => act(() => api(`/mcp/grants/${g.id}`, { method: "DELETE" }))}>Revoke</Button></td></tr>
          ))}
        </tbody></table>
      )}
      <div className="flex flex-wrap gap-2">
        <select aria-label="Grant tool" className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-[#070d1f]" value={tool} onChange={(e) => setTool(e.target.value)}>
          <option value="*">* (all tools)</option>{server.tools.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
        </select>
        <select aria-label="Grant role" className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-[#070d1f]" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">Role</option>{roles.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <Button variant="secondary" disabled={!role} onClick={() => act(() => api("/mcp/grants", { json: { server_id: server.id, tool_name: tool, role } }))}>Grant</Button>
      </div>
      <ErrorNote message={error} />
    </div>
  );
}
