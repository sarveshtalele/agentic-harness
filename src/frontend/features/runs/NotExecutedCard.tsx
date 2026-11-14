import { Download } from "lucide-react";
import { Badge } from "../../components/ui";

// Gate 5 of a brownfield run: nothing was executed, so there is no pass or fail, only validity and a download.
export function NotExecutedCard({ payload }: { payload: any }) {
  const s = payload.summary;
  return (
    <div className="space-y-3 rounded-xl border border-slate-300 bg-white/80 p-3 dark:border-slate-700 dark:bg-[#070d1f]" data-testid="not-executed">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge tone="slate">{s.verdict}</Badge>
        <span>{s.valid} of {s.tests} tests valid, {s.needs_review} need review. {s.requirements_with_valid_test} of {s.requirements} requirements have a valid test.</span>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400">Failed checks: {Object.entries(s.by_check || {}).map(([k, v]) => `${k} ${v}`).join(", ")}. The platform did not run the tests: run them on your own systems with <code className="mono">{payload.run_command}</code>.</p>
      {payload.plugin_check?.note && <p className="text-xs text-slate-600 dark:text-slate-400" data-testid="plugin-check-5">Plugin Gate 5 check: {payload.plugin_check.note}.</p>}
      <div className="max-h-64 overflow-auto rounded-lg border border-slate-100 dark:border-slate-800">
        <table className="w-full text-left text-xs" data-testid="validity-matrix">
          <thead className="bg-slate-50 text-slate-600 dark:bg-slate-900 dark:text-slate-400"><tr><th className="p-2">Requirement</th><th className="p-2">Cases and test files</th><th className="p-2">Validity</th></tr></thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {(payload.matrix_rows || []).map((r: any) => (
              <tr key={r.requirement_id}>
                <td className="p-2">{r.requirement_id} ({r.priority}) {r.title}</td>
                <td className="mono p-2 break-all">{r.cases.map((c: any) => `${c.case_id}: ${c.test_file || "no test"}`).join("; ")}</td>
                <td className="p-2">{r.cases.map((c: any) => c.result + (c.failed_checks?.length ? ` (${c.failed_checks.join("/")})` : "")).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <a href={payload.tests_zip} download className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700" data-testid="download-tests">
        <Download className="h-4 w-4" /> Download tests (zip)
      </a>
    </div>
  );
}
