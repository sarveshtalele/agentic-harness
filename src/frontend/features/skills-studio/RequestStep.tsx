import { Button, Card, Field, inputClass } from "../../components/ui";
import { CallStatus, Call } from "./useCall";

export function RequestStep({ request, onRequest, ready, call, onDraft }: { request: string; onRequest: (v: string) => void; ready: boolean; call: Call; onDraft: () => void }) {
  return (
    <Card title="3. Request and plan">
      <div className="space-y-3">
        <Field label="What should the skill do?" hint="The model drafts a plan from this and the source. Nothing is written until you approve the plan.">
          <textarea className={`${inputClass} h-24`} value={request} onChange={(e) => onRequest(e.target.value)} data-testid="studio-request" />
        </Field>
        {!ready && <p className="text-xs text-slate-500">Choose a project, a source and a kind first.</p>}
        <Button onClick={onDraft} disabled={!ready || !!call.busy} busy={!!call.busy} data-testid="studio-draft-plan">Draft plan</Button>
        <CallStatus call={call} />
      </div>
    </Card>
  );
}
