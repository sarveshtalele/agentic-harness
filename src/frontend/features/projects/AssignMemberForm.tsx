"use client";

import { UserPlus } from "lucide-react";
import { useState } from "react";
import { api } from "../../lib/api";
import { Button, Field, inputClass } from "../../components/ui";

const MEMBER_ROLES = [["developer", "Developer"], ["qe_lead", "QE lead"], ["ba", "BA"], ["viewer", "Viewer"]];

export function AssignMemberForm({ projectId, run }: { projectId: string; run: (work: () => Promise<unknown>) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("developer");
  return (
    <div className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/30 space-y-2">
      <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
        Assign Collaborator Access Policy
      </span>
      <div className="flex flex-wrap items-end gap-2">
        <Field label="Directory Username" hint="Must be pre-provisioned by Administrator.">
          <input
            name="member-username"
            autoComplete="off"
            placeholder="e.g. jdoe"
            className={inputClass}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </Field>
        <Field label="Governance Policy">
          <select
            name="member-role"
            className={inputClass}
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {MEMBER_ROLES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </Field>
        <Button
          disabled={!username.trim()}
          onClick={() =>
            run(async () => {
              await api(`/projects/${projectId}/members`, {
                json: { username: username.trim(), role },
              });
              setUsername("");
            })
          }
        >
          <UserPlus className="h-4 w-4" /> Assign Policy
        </Button>
        {!username.trim() && <span className="text-xs text-slate-600 dark:text-slate-400">Enter a username to enable.</span>}
      </div>
    </div>
  );
}
