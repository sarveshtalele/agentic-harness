import { Button, Card, ErrorNote, Field, inputClass } from "../../components/ui";

export function AgentControlsCard({ item, user, reason, setReason, limit, setLimit, model, setModel, choices, error, save }: { item: any; user: any; reason: string; setReason: (v: string) => void; limit: string; setLimit: (v: string) => void; model: string; setModel: (v: string) => void; choices: string[]; error: string; save: (enabled: boolean) => void }) {
  return (
    <Card title="Controls">
      <div className="mt-3 grid gap-2 md:grid-cols-4">
        <Field label="Signing as"><p className="py-2 text-sm font-semibold" data-testid="signing-as">{user.username}</p></Field>
        <Field label="Reason"><input className={inputClass} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
        <Field label="Tokens per model call"><input type="number" min={500} max={64000} className={inputClass} value={limit} onChange={(e) => setLimit(e.target.value)} /></Field>
        <Field label="Model"><select className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} data-testid="agent-model"><option value="">Each user&apos;s default</option>{[...new Set([...choices, ...(model ? [model] : [])])].map((m) => <option key={m} value={m}>{m}</option>)}</select></Field>
      </div>
      <ErrorNote message={error} />
      <div className="mt-2 flex gap-2">
        <Button variant="secondary" onClick={() => save(item.enabled)}>Save limit</Button>
        {item.enabled ? <Button variant="danger" disabled={!reason.trim()} onClick={() => save(false)}>Disable agent</Button> : <Button variant="success" onClick={() => save(true)}>Enable agent</Button>}
      </div>
    </Card>
  );
}
