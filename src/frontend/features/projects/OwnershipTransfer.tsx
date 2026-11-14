import { Button, Field, inputClass } from "../../components/ui";

export function OwnershipTransfer({ newOwner, setNewOwner, onTransfer }: { newOwner: string; setNewOwner: (v: string) => void; onTransfer: () => void }) {
  return (
    <div className="mt-2 border-t border-slate-200 pt-3 dark:border-slate-800">
      <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
        Project Ownership Governance
      </span>
      <div className="mt-1.5 flex flex-wrap items-end gap-2">
        <Field label="Transfer ownership to" hint="Admin only. Logged in the audit ledger. The current owner loses ownership.">
          <input
            name="transfer-username"
            autoComplete="off"
            placeholder="admin-provisioned username"
            className={inputClass}
            value={newOwner}
            onChange={(e) => setNewOwner(e.target.value)}
          />
        </Field>
        <Button
          variant="danger"
          disabled={!newOwner.trim()}
          onClick={onTransfer}
        >
          Transfer Ownership
        </Button>
        {!newOwner.trim() && <span className="text-xs text-slate-600 dark:text-slate-400">Enter a username to enable.</span>}
      </div>
    </div>
  );
}
