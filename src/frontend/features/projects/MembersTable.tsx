import { Trash2 } from "lucide-react";
import { Badge, Button } from "../../components/ui";

const roleCapabilityMap: Record<string, string> = {
  owner: "Full governance, gate signoff, repo write, collaborator assignment",
  admin: "Cross-project policy management, MCP tool provisioning, token bypass",
  lead_architect: "G0-G3 approvals, test design review, baseline signoff",
  developer: "Code edit proposals, bug diagnosis, branch checkout",
  qa_engineer: "Test generation execution, JUnit oracle verification, bug fixes",
  viewer: "Read-only inspection of documents, traces, and metrics",
};

export function MembersTable({ items, onRevoke }: { items: any[] | null; onRevoke: (member: any) => void }) {
  return items && items.length ? (
    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
      <table className="w-full text-left text-xs">
        <thead className="border-b border-slate-200 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-900/50 text-slate-500">
          <tr>
            <th className="py-2 px-3 font-semibold">User</th>
            <th className="py-2 px-3 font-semibold">Assigned Policy / Role</th>
            <th className="py-2 px-3 font-semibold">Capabilities</th>
            <th className="py-2 px-3 text-right font-semibold">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
          {items.map((m) => (
            <tr key={m.user_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/30">
              <td className="py-2.5 px-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                    {(m.username || "U")[0].toUpperCase()}
                  </div>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{m.username}</span>
                </div>
              </td>
              <td className="py-2.5 px-3">
                <Badge tone="indigo">{(m.role || "").replace("_", " ")}</Badge>
              </td>
              <td className="py-2.5 px-3 text-[11px] text-slate-500 dark:text-slate-400">
                {roleCapabilityMap[m.role] || "Standard repository access"}
              </td>
              <td className="py-2.5 px-3 text-right">
                <Button
                  variant="secondary"
                  className="!p-1 text-slate-400 hover:text-rose-500"
                  aria-label={`Revoke policy for ${m.username}`}
                  onClick={() => onRevoke(m)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <div className="rounded-xl border border-dashed border-slate-200 p-3 text-center text-xs text-slate-500 dark:border-slate-800">
      No external collaborators assigned. Restricted to project owner and administrators.
    </div>
  );
}
