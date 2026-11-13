"use client";

import { useEffect, useState } from "react";
import { Badge, Card, Empty, ErrorNote, Spinner } from "../../components/ui";
import { api } from "../../lib/api";

const RESULT_TONE: Record<string, "emerald" | "rose" | "slate" | "amber"> = { passed: "emerald", failed: "rose", "not run": "slate" };

/** Requirement -> scenario -> case -> test -> result, gaps first (plan 12.5), from the coverage map the agentic-qe plugin
 * writes in the workspace. Each link opens the real file read-only. */
export function TraceView({ projectId }: { projectId: string }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => { api(`/projects/${projectId}/qe/trace`).then(setData).catch((e) => setError(e.message)); }, [projectId]);
  const file = (path: string, label?: string) => (
    <a className="mono text-indigo-600 underline dark:text-indigo-400" target="_blank" rel="noopener noreferrer"
      href={`/api/projects/${projectId}/qe/file?path=${encodeURIComponent(path)}`}>{label || path}</a>
  );
  return (
    <Card title="Traceability">
      <ErrorNote message={error} />
      {!data ? (!error && <Spinner label="Reading the coverage map" />) : !data.apps.length ? <Empty title="No trace yet">{data.note}</Empty> : data.apps.map((app: any) => (
        <section key={app.app} className="space-y-3" data-testid="trace-app">
          {app.error ? <ErrorNote message={app.error} /> : (
            <>
              <div className="flex flex-wrap gap-1.5 text-xs">
                {app.checks.map((c: any) => <Badge key={c.gate} tone={c.ok ? "emerald" : "rose"}>{`G${c.gate} ${c.ok ? "PASS" : "FAIL"}`}</Badge>)}
                <span className="text-slate-500">{app.app}: {app.counts.requirements} requirements, {app.counts.scenarios} scenarios, {app.counts.cases} cases, {app.counts.tests} test files, {app.counts.results} results</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs" data-testid="trace-table">
                  <thead className="text-slate-500"><tr>{["Requirement", "Source", "Scenarios", "Cases and tests", "Status"].map((h) => <th key={h} className="px-1.5 py-1">{h}</th>)}</tr></thead>
                  <tbody>{app.rows.map((r: any) => (
                    <tr key={r.id} className="border-t border-slate-200 align-top dark:border-slate-800" data-testid="trace-row">
                      <td className="px-1.5 py-1"><b>{r.id}</b> {r.priority && <Badge>{r.priority}</Badge>}<p className="text-slate-600 dark:text-slate-300">{r.text}</p></td>
                      <td className="px-1.5 py-1">{r.source?.file ? <>{file(r.source.file, `${r.source.file}${r.source.line ? `:${r.source.line}` : ""}`)}<p className="mono text-slate-500" title={r.source.quote}>{r.source.quote}</p></> : "—"}
                        {r.quote_found === false && <p className="text-rose-600">quote not found in the file</p>}</td>
                      <td className="mono px-1.5 py-1">{r.scenarios.join(", ") || "—"}</td>
                      <td className="px-1.5 py-1">{r.cases.length ? r.cases.map((c: any) => (
                        <p key={c.case_id}><span className="mono">{c.case_id}</span> {c.tests.length ? c.tests.map((t: string) => <span key={t}> {file(t)}</span>) : <span className="text-slate-500"> no test</span>}{" "}
                          <Badge tone={RESULT_TONE[c.result] || "amber"}>{c.result}</Badge></p>
                      )) : "—"}</td>
                      <td className="px-1.5 py-1">{r.gap ? <Badge tone="rose">{r.gap}</Badge> : <Badge tone="emerald">covered</Badge>}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              {app.evidence.length > 0 && <p className="text-xs">Evidence: {app.evidence.map((p: string) => <span key={p}> {file(p, p.split("/").slice(-2).join("/"))}</span>)}</p>}
              {app.orphan_tests.length > 0 && <p className="text-xs text-amber-600">Test files with no case marker: {app.orphan_tests.join(", ")}</p>}
            </>
          )}
        </section>
      ))}
    </Card>
  );
}
