import { useEffect, useState } from "react";
import { Badge, Button, Card, ConfirmModal, Field, inputClass } from "../../components/ui";
import { api } from "../../lib/api";
import { EvalCases } from "./EvalCasesEditor";
import { Files, Formats, Subagents, Tasks } from "./PlanLists";
import { Plan, PlanRecord } from "./types";
import { CallStatus, useCall } from "./useCall";

export function PlanEditor({ record, onRecord }: { record: PlanRecord; onRecord: (r: PlanRecord) => void }) {
  const [plan, setPlan] = useState<Plan>(record.plan);
  const [confirm, setConfirm] = useState(false);
  const call = useCall();
  useEffect(() => setPlan(record.plan), [record]);
  const draft = record.status === "draft";
  const dirty = JSON.stringify(plan) !== JSON.stringify(record.plan);
  const save = () => call.run("Saving…", async () => onRecord(await api(`/skill-studio/plans/${record.id}`, { method: "PATCH", json: { plan } })));
  const approve = async () => {
    await call.run("Approving…", async () => onRecord(await api(`/skill-studio/plans/${record.id}/approve`, { method: "POST" })));
    setConfirm(false);
  };
  const over = plan.description.length > 1024;
  return (
    <Card title="4. Review and edit the plan" actions={<Badge>{record.status}</Badge>}>
      <div className="space-y-4">
        {!draft && record.plan_sha256 && (
          <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm" data-testid="studio-approved">
            Plan approved. SHA-256 <span className="mono" data-testid="studio-plan-hash" title={record.plan_sha256}>{record.plan_sha256.slice(0, 12)}</span>, approved by {record.approved_by}. It can no longer be edited.
          </p>
        )}
        <fieldset disabled={!draft || !!call.busy} className="min-w-0 space-y-4 border-0 p-0 disabled:opacity-60">
          <Field label="Name"><input aria-label="Skill name" className={inputClass} data-testid="studio-plan-name" value={plan.name} onChange={(e) => setPlan({ ...plan, name: e.target.value })} /></Field>
          <Field label="Description" hint={`${plan.description.length} / 1024 characters`}>
            <textarea aria-label="Skill description" className={`${inputClass} h-24 ${over ? "border-rose-500" : ""}`} value={plan.description} onChange={(e) => setPlan({ ...plan, description: e.target.value })} />
          </Field>
          <Tasks plan={plan} onChange={setPlan} />
          <Files plan={plan} onChange={setPlan} />
          <Subagents plan={plan} onChange={setPlan} />
          <Formats plan={plan} onChange={setPlan} />
          <EvalCases plan={plan} onChange={setPlan} />
        </fieldset>
        {draft && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={save} disabled={!dirty || !!call.busy} data-testid="studio-save">Save changes</Button>
            <Button onClick={() => setConfirm(true)} disabled={dirty || !!call.busy} data-testid="studio-approve">Approve plan</Button>
            {dirty && <span className="self-center text-xs text-slate-500">Save your changes before approving.</span>}
          </div>
        )}
        <CallStatus call={call} />
      </div>
      <ConfirmModal open={confirm} variant="primary" title="Approve this plan" confirmLabel="Approve plan" busy={!!call.busy} onConfirm={approve} onCancel={() => setConfirm(false)}
        message="The plan is hashed and locked. Files are generated only from this exact plan. To change it later you start a new plan." />
    </Card>
  );
}
