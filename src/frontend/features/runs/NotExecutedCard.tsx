import { Download } from "lucide-react";
import { Badge } from "../../components/ui";
import { checkLabel, VERDICTS } from "../../lib/labels";

const Check = ({ code }: { code: string }) => <abbr title={checkLabel(code)} className="cursor-help underline decoration-dotted">{code}</abbr>;

// Gate 5 of a brownfield run: nothing was executed, so there is no pass or fail, only validity and a download.
export function NotExecutedCard({ payload }: { payload: any }) {
  const s = payload.summary;
  const failed = Object.entries(s.by_check || {}).filter(([, v]) => Number(v) > 0);
  return (
    <div className="space-y-3 rounded-xl border border-slate-300 bg-white/80 p-3 dark:border-slate-700 dark:bg-[#070d1f]" data-testid="not-executed">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge tone="slate">{s.verdict}</Badge>
        <span>{s.valid} of {s.tests} tests valid, {s.needs_review} need review. {s.requirements_with_valid_test} of {s.requirements} requirements have a valid test.</span>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400">{VERDICTS[s.verdict]}</p>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        {failed.length ? <>Failed checks: {failed.map(([k, v], i) => <span key={k}>{i ? ", " : ""}<Check code={k} /> {String(v)}</span>)}. </> : "No check failed. "}
        The platform did not run the tests: run them on your own systems with <code className="mono break-all">{payload.run_command}</code>.
      </p>
      {payload.plugin_check?.note && <p className="text-xs text-slate-600 dark:text-slate-400" data-testid="plugin-check-5">Plugin Gate 5 check: {payload.plugin_check.note}.</p>}
      <div className="max-h-64 overflow-auto rounded-lg border border-slate-100 dark:border-slate-800">
        <table className="w-full min-w-[34rem] text-left text-xs" data-testid="validity-matrix">
          <thead className="sticky top-0 bg-slate-50 text-slate-600 dark:bg-slate-900 dark:text-slate-400"><tr><th className="p-2">Requirement</th><th className="p-2">Case and test file</th><th className="p-2">Validity</th></tr></thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {(payload.matrix_rows || []).map((r: any) => (
              <tr key={r.requirement_id} className="align-top">
                <td className="p-2">{r.requirement_id} ({r.priority}) {r.title}</td>
                <td className="p-2">{r.cases.map((c: any) => <div key={c.case_id} className="break-all"><b>{c.case_id}</b> {c.test_file ? <span className="mono" title={c.test_file}>{c.test_file}</span> : <span className="text-slate-500">No test file</span>}</div>)}</td>
                <td className="p-2">{r.cases.map((c: any) => <div key={c.case_id} className="flex flex-wrap items-center gap-1">
                  <Badge tone={c.result === "valid" ? "emerald" : c.result === "no test" ? "slate" : "amber"}>{c.result === "valid" ? "Valid" : c.result === "no test" ? "No test" : "Needs review"}</Badge>
                  {c.failed_checks?.map((k: string) => <Check key={k} code={k} />)}
                </div>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">{(payload.matrix_rows || []).length} requirement rows. Scroll the table for more.</p>
      <div className="flex flex-wrap items-center gap-3">
        <a href={payload.tests_zip} download className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700" data-testid="download-tests">
          <Download className="h-4 w-4" /> Download tests (zip)
        </a>
        <span className="text-xs text-slate-600 dark:text-slate-400">A ZIP of the generated test files.</span>
      </div>
    </div>
  );
}
