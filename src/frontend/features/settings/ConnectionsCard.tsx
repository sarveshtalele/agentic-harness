import { Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card, ErrorNote, Field, inputClass, useToast } from "../../components/ui";
import { api } from "../../lib/api";

export function ConnectionsCard() {
  const [connections, setConnections] = useState<any[]>([]);
  const [token, setToken] = useState("");
  const [label, setLabel] = useState("");
  const [error, setError] = useState("");
  const toast = useToast();
  const loadConnections = useCallback(() => api("/connections").then(setConnections), []);
  useEffect(() => {
    loadConnections();
  }, [loadConnections]);
  const connect = async () => {
    setError("");
    try {
      const created = await api("/connections/github", { json: { token, label } });
      setToken("");
      setLabel("");
      loadConnections();
      toast(`Connected as ${created.login}`);
    } catch (e: any) {
      setError(e.message);
    }
  };
  return (
  <Card title="Private repository access">
    <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">Create a GitHub fine-grained personal access token with read access to the repository contents, plus write access to contents and pull requests if you want Agentic QE Platform to open pull requests. It is checked against GitHub, encrypted at rest, and never placed in URLs or clone config.</p>
    <div className="space-y-3">
      <Field label="Label"><input className={inputClass} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Work GitHub" /></Field>
      <Field label="GitHub token"><input type="password" autoComplete="off" className={inputClass} value={token} onChange={(e) => setToken(e.target.value)} /></Field>
      <ErrorNote message={error} />
      <Button onClick={connect} disabled={token.length < 8}>Validate and save</Button>
    </div>
    {connections.length > 0 && (
      <ul className="mt-3 divide-y divide-slate-200 text-sm dark:divide-slate-800">{connections.map((c) => (
        <li key={c.id} className="flex items-center justify-between py-1.5"><span>{c.label} <span className="text-xs text-slate-500">({c.login})</span></span><button aria-label={`Remove ${c.label}`} onClick={() => api(`/connections/${c.id}`, { method: "DELETE" }).then(loadConnections)} className="text-slate-400 hover:text-rose-500"><Trash2 className="h-4 w-4" /></button></li>
      ))}</ul>
    )}
  </Card>
  );
}
