"use client";

import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../../components/AuthGate";
import { Badge, Card, ErrorNote } from "../../components/ui";
import { ConfirmModal } from "../../components/ConfirmModal";
import { api } from "../../lib/api";
import { AssignMemberForm } from "./AssignMemberForm";
import { MembersTable } from "./MembersTable";
import { OwnershipTransfer } from "./OwnershipTransfer";

/** Who may do what in this project: members and their roles, recorded in the ledger. */
export function ProjectGovernanceAccess({ project, refresh }: { project: any; refresh: () => void }) {
  const { user } = useAuth();
  const [items, setItems] = useState<any[] | null>(null);
  const [newOwner, setNewOwner] = useState("");
  const [memberToRemove, setMemberToRemove] = useState<any | null>(null);
  const [confirmTransferModal, setConfirmTransferModal] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    api(`/projects/${project.id}/members`)
      .then((res) => setItems(Array.isArray(res) ? res : []))
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, [project.id]);

  const run = async (work: () => Promise<unknown>) => {
    setError("");
    try {
      await work();
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-indigo-500" />
            Access and roles
          </span>
          <Badge tone="indigo">Policy Enforced</Badge>
        </div>
      }
    >
      <div data-testid="governance-access" className="space-y-4">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Features and execution boundaries are tracked per user profile. Only directory users provisioned by an Administrator can be assigned as project collaborators.
        </p>

        <MembersTable items={items} onRevoke={setMemberToRemove} />

        <AssignMemberForm projectId={project.id} run={run} />

        {user.role === "admin" && <OwnershipTransfer newOwner={newOwner} setNewOwner={setNewOwner} onTransfer={() => setConfirmTransferModal(true)} />}

        <ErrorNote message={error} />
      </div>

      {/* Confirm Member Removal Modal */}
      <ConfirmModal
        isOpen={!!memberToRemove}
        title="Revoke Project Access Policy"
        description={`Are you sure you want to revoke project access for "${memberToRemove?.username}"? Their role permissions and gate approvals delegation will be terminated.`}
        confirmText="Revoke Policy"
        tone="danger"
        onConfirm={async () => {
          if (memberToRemove) {
            await run(() => api(`/projects/${project.id}/members/${memberToRemove.user_id}`, { method: "DELETE" }));
            setMemberToRemove(null);
          }
        }}
        onClose={() => setMemberToRemove(null)}
      />

      {/* Confirm Ownership Transfer Modal */}
      <ConfirmModal
        isOpen={confirmTransferModal}
        title="Transfer Project Ownership"
        description={`Are you sure you want to transfer ownership of this project to "${newOwner}"? You will relinquish owner administrative privileges.`}
        confirmText="Confirm Transfer"
        tone="danger"
        onConfirm={async () => {
          await run(async () => {
            await api(`/projects/${project.id}/transfer`, { json: { username: newOwner.trim() } });
            setNewOwner("");
            refresh();
          });
          setConfirmTransferModal(false);
        }}
        onClose={() => setConfirmTransferModal(false)}
      />
    </Card>
  );
}
