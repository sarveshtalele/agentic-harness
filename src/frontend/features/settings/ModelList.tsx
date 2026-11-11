import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, ErrorNote, Field, inputClass, useToast } from "../../components/ui";
import { api, when } from "../../lib/api";

/** The models on the one endpoint. A listed name may not work, so loaded names start off and each has a Test that sends a real short completion. */
export function ModelList() {
  const [items, setItems] = useState<any[] | null>(null);
  const [name, setName] = useState("");
  const [zone, setZone] = useState("");
  const [results, setResults] = useState<Record<string, any>>({});
  const [testing, setTesting] = useState("");
  const [checking, setChecking] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();
  const load = useCallback(() => api("/models").then(setItems).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
    api("/settings/timezone").then((z) => setZone(z.timezone));
  }, [load]);
  const guard = async (work: () => Promise<unknown>) => {
    setError("");
    try {
      await work();
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };
  const patch = (model: string, json: object) => guard(() => api("/models", { method: "PATCH", json: { name: model, ...json } }));
  const test = async (model: string) => {
    setTesting(model);
    setResults((r) => ({ ...r, [model]: undefined }));
    try {
      const outcome = await api("/settings/llm/test", { json: { model } });
      setResults((r) => ({ ...r, [model]: outcome }));
    } catch (e: any) {
      setResults((r) => ({ ...r, [model]: { ok: false, error: e.message } }));
    }
    setTesting("");
  };
  const checkTools = async (model: string) => {
    setChecking(model);
    await guard(async () => { await api("/models/tool-check", { json: { name: model } }); });
    setChecking("");
  };
  const loadFromProxy = async () => {
    setLoading(true);
    await guard(async () => {
      const found = await api("/models/load", { method: "POST" });
      toast(`${found.listed} models listed, ${found.added.length} new. They are switched off until you test and enable them.`);
    });
    setLoading(false);
  };
  return (
    <Card title="Models" actions={<Button variant="secondary" busy={loading} onClick={loadFromProxy}>Load from proxy</Button>}>
      <div className="space-y-3" data-testid="model-list">
        <p className="text-xs text-slate-500">All models use the URL and key above. Switch a model on only after its test works. Each user may use only the models ticked for them on the Users page.</p>
        {items === null ? null : items.length === 0 ? <p className="text-sm text-slate-500" data-testid="models-empty">No models yet. Add one by name, or load the names your proxy offers.</p> : (
          <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
            {items.map((m) => (
              <li key={m.name} className="space-y-1 py-2">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="mono min-w-0 flex-1 truncate text-xs font-semibold">{m.name}</span>
                  <label className="flex items-center gap-1 text-xs"><input type="checkbox" aria-label={`Enable ${m.name}`} checked={m.enabled} onChange={(e) => patch(m.name, { enabled: e.target.checked })} />On</label>
                  <label className="flex items-center gap-1 text-xs"><input type="radio" name="default-model" aria-label={`Default ${m.name}`} checked={m.is_default} disabled={!m.enabled} onChange={() => patch(m.name, { is_default: true })} />Default</label>
                  <Button variant="secondary" className="!px-2 !py-1 !text-xs" busy={testing === m.name} onClick={() => test(m.name)}>Test</Button>
                  <Button variant="secondary" className="!px-2 !py-1 !text-xs" busy={checking === m.name} onClick={() => checkTools(m.name)}>Check tools</Button>
                  <button aria-label={`Remove ${m.name}`} onClick={() => guard(() => api(`/models?name=${encodeURIComponent(m.name)}`, { method: "DELETE" }))} className="text-slate-400 hover:text-rose-500"><Trash2 className="h-4 w-4" /></button>
                </div>
                <p className="text-xs" data-testid={`tool-status-${m.name}`}>
                  Tools: {m.tools_status === "passed" ? <b className="text-emerald-600 dark:text-emerald-400">passed</b> : m.tools_status === "failed" ? <b className="text-rose-500">failed</b> : <span className="text-slate-500">not checked</span>}
                  {m.tools_status && <span className="text-slate-500"> ({m.tools_reason}) checked {when(m.tools_checked_at)}, max_tokens {m.tools_max_tokens}</span>}
                </p>
                {results[m.name] && (results[m.name].ok ? <p className="text-xs text-emerald-600 dark:text-emerald-400">Works: replied in {results[m.name].latency_ms} ms, {results[m.name].tokens} tokens. Reply: {results[m.name].reply}</p> : <p role="alert" className="text-xs text-rose-500">{results[m.name].error}</p>)}
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap items-end gap-2">
          <Field label="Add a model by name"><input name="add-model" className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="deepseek-v4-flash-global" /></Field>
          <Button disabled={!name.trim()} onClick={() => guard(async () => { await api("/models", { json: { name } }); setName(""); })}><Plus className="h-4 w-4" /> Add</Button>
        </div>
        <ErrorNote message={error} />
        <div className="flex flex-wrap items-end gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
          <Field label="Time zone for token limits" hint="Days reset at midnight, weeks on Monday, months on the 1st, in this zone."><input name="timezone" className={inputClass} value={zone} onChange={(e) => setZone(e.target.value)} /></Field>
          <Button variant="secondary" onClick={() => guard(async () => { await api("/settings/timezone", { method: "PUT", json: { timezone: zone } }); toast("Time zone saved"); })}>Save zone</Button>
        </div>
      </div>
    </Card>
  );
}
