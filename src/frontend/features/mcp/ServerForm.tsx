import { useEffect, useState } from "react";
import { Button, Card, ErrorNote, Field, inputClass } from "../../components/ui";
import { api } from "../../lib/api";
import { KeyValueRows } from "./KeyValueRows";
import { Row, Template } from "./types";

const toMap = (rows: Row[]) => Object.fromEntries(rows.filter((r) => r.key.trim()).map((r) => [r.key.trim(), r.value]));
const names = (list?: string[]): Row[] => (list || []).map((key) => ({ key, value: "" }));

/** Add a server. A catalog template only pre-fills the fields; nothing is registered until an admin saves. */
export function ServerForm({ prefill, stdioAllowed, onAdded, onCancel }: { prefill: Template | null; stdioAllowed: boolean; onAdded: () => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [transport, setTransport] = useState(stdioAllowed ? "stdio" : "http");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState<string[]>([]);
  const [url, setUrl] = useState("");
  const [env, setEnv] = useState<Row[]>([]);
  const [headers, setHeaders] = useState<Row[]>([]);
  const [oauth, setOauth] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!prefill) return;
    setName(prefill.name); setTransport(prefill.transport); setCommand(prefill.command || ""); setArgs(prefill.args || []);
    setUrl(prefill.url || ""); setEnv(names(prefill.env_names)); setHeaders(names(prefill.header_names));
  }, [prefill]);
  const stdio = transport === "stdio";
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError("");
    try {
      await api("/mcp/servers", { json: stdio ? { name, transport, command, args, env: toMap(env) } : { name, transport, url, headers: toMap(headers), auth: oauth && transport === "http" ? "oauth" : "none" } });
      onAdded();
    } catch (err: any) { setError(err.message); } finally { setBusy(false); }
  };
  return (
    <Card title="Add MCP server">
      <form onSubmit={submit} className="space-y-3" data-testid="mcp-add-form">
        <Field label="Name"><input className={inputClass} required value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Transport" hint={stdioAllowed ? undefined : "stdio servers run only in local development"}>
          <select className={inputClass} value={transport} onChange={(e) => setTransport(e.target.value)}>
            <option value="stdio" disabled={!stdioAllowed}>stdio</option><option value="http">http</option><option value="websocket">websocket</option>
          </select>
        </Field>
        {stdio ? (
          <>
            <Field label="Command"><input className={inputClass} required value={command} onChange={(e) => setCommand(e.target.value)} /></Field>
            <div className="space-y-1">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Arguments, one per row</span>
              {args.map((a, i) => (
                <div key={i} className="flex gap-2">
                  <input className={inputClass} aria-label={`Argument ${i + 1}`} value={a} onChange={(e) => setArgs(args.map((x, j) => (j === i ? e.target.value : x)))} />
                  <Button type="button" variant="secondary" onClick={() => setArgs(args.filter((_, j) => j !== i))}>Remove</Button>
                </div>
              ))}
              <Button type="button" variant="secondary" onClick={() => setArgs([...args, ""])}>Add argument</Button>
            </div>
            <KeyValueRows label="Environment variable" rows={env} onChange={setEnv} secret />
          </>
        ) : (
          <>
            <Field label="URL"><input className={inputClass} required value={url} onChange={(e) => setUrl(e.target.value)} /></Field>
            <KeyValueRows label="Header" rows={headers} onChange={setHeaders} secret />
            {transport === "http" && (
              <label className="flex items-center gap-2 text-xs">
                <input type="checkbox" checked={oauth} onChange={(e) => setOauth(e.target.checked)} />
                Each member signs in with OAuth (for example the Atlassian remote MCP, https://mcp.atlassian.com/v2/mcp)
              </label>
            )}
          </>
        )}
        <ErrorNote message={error} />
        <div className="flex gap-2"><Button type="submit" busy={busy}>Add server</Button><Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button></div>
      </form>
    </Card>
  );
}
