import { useEffect, useState } from "react";
import { Button, ErrorNote, inputClass } from "../../components/ui";
import { api } from "../../lib/api";
import { Server, Tool } from "./types";

/** Calls one tool for real, as the signed-in user, on a project. Shows what came back, or the server's own error. */
export function TryTool({ server, tool }: { server: Server; tool: Tool }) {
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([]);
  const [projectId, setProjectId] = useState("");
  const [text, setText] = useState("{}");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ content: unknown; latency_ms: number } | null>(null);
  useEffect(() => {
    api("/projects").then((r) => { const list = Array.isArray(r) ? r : r?.projects || []; setProjects(list); setProjectId((p) => p || list[0]?.id || ""); }).catch((e) => setError(e.message));
  }, []);
  const run = async () => {
    setError(""); setResult(null);
    let args: unknown;
    try { args = JSON.parse(text); } catch { setError("The arguments are not valid JSON."); return; }
    setBusy(true);
    try { const r = await api(`/mcp/servers/${server.id}/tools/${encodeURIComponent(tool.name)}/call`, { json: { project_id: projectId, arguments: args } }); setResult(r); }
    catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-2 rounded-lg bg-slate-500/5 p-3" data-testid="mcp-try">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="space-y-2">
          <select aria-label="Project" className={inputClass} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            {projects.length === 0 && <option value="">No projects</option>}{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <textarea aria-label="Arguments (JSON)" rows={5} className={`${inputClass} mono`} value={text} onChange={(e) => setText(e.target.value)} />
          <Button busy={busy} disabled={!projectId} onClick={run}>Run</Button>
        </div>
        <pre className="mono max-h-40 overflow-auto text-xs text-slate-500" aria-label="Input schema">{JSON.stringify(tool.input_schema, null, 2)}</pre>
      </div>
      <ErrorNote message={error} />
      {result && <div data-testid="mcp-try-result"><p className="text-xs text-slate-500">{result.latency_ms} ms</p><pre className="mono max-h-60 overflow-auto text-xs">{typeof result.content === "string" ? result.content : JSON.stringify(result.content, null, 2)}</pre></div>}
    </div>
  );
}
