import { Badge } from "../../components/ui";
import { cleanTestName, verdictTone } from "./lib";

/** One row per case, as code judged it: the total is the sum of the scores and the verdict follows the rule, whatever the reviewer wrote. */
function CaseTable({ records }: { records: any[] }) {
  return (
    <div className="max-h-96 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700" data-testid="case-table">
      <table className="w-full text-left text-xs table-fixed">
        <thead className="sticky top-0 bg-slate-100 dark:bg-slate-800">
          <tr>
            <th className="p-2 w-28 font-semibold">Case</th>
            <th className="p-2 w-20 font-semibold">Total</th>
            <th className="p-2 w-24 font-semibold">Verdict</th>
            <th className="p-2 w-36 font-semibold">Evidence</th>
            <th className="p-2 w-16 font-semibold">Low</th>
            <th className="p-2 min-w-[240px] font-semibold">Flaws, with file, line and fix</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r: any) => (
            <tr key={r.tc_id} className="border-t border-slate-200 align-top dark:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/40" data-testid="case-row" data-verdict={r.verdict}>
              <td className="mono p-2 truncate" title={r.tc_id}>{r.tc_id}{r.round === 2 && <span className="ml-1 text-[10px] text-slate-500">revised</span>}</td>
              <td className="p-2">{r.total === null || r.total === undefined ? "not run" : <>{r.total}{r.capped && <span className="ml-1 text-[10px] text-rose-500">capped</span>}</>}</td>
              <td className="p-2"><Badge tone={verdictTone(r.verdict)}>{r.verdict}</Badge></td>
              <td className="p-2 truncate mono text-[11px] text-slate-600 dark:text-slate-400" title={r.evidence}>{cleanTestName(r.evidence)}</td>
              <td className="p-2" title={r.low_reason}>{r.low ? "low" : ""}</td>
              <td className="p-2 break-words">
                {(r.flaws || []).map((f: any, i: number) => (
                  <div key={i} className="mb-1 text-slate-700 dark:text-slate-300">
                    <span className="mono font-medium text-slate-900 dark:text-slate-100">
                      {f.file ? `${cleanTestName(f.file)}${f.line ? `:${f.line}` : ""}` : cleanTestName(f.evidence)}
                    </span>
                    {f.dimension ? `: ${f.dimension}. ` : ": "}
                    <span className="text-slate-600 dark:text-slate-400">Fix: {f.fix}</span>
                  </div>
                ))}
                {(r.problems || []).map((p: string, i: number) => <div key={`p${i}`} className="text-slate-500">{p}</div>)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ConfidenceNote({ review }: { review?: any }) {
  if (!review) return null;
  const tone = review.score === null ? "amber" : review.score >= 85 ? "emerald" : review.score >= 70 ? "amber" : "rose";
  const c = review.counts;
  return (
    <div className="space-y-1.5 text-sm" data-testid="confidence">
      <span className="flex flex-wrap items-center gap-2"><b>Independent confidence review</b> <Badge tone={tone}>{review.score === null ? "not run" : `${review.score} of 100`}</Badge> <Badge>{review.verdict}</Badge></span>
      {c && <p className="text-xs text-slate-600 dark:text-slate-400" data-testid="confidence-counts">{c.cases} reviewed: {c.approved} approved, {c.revise} revise, {c.reject} reject, {c.not_run} not run. {c.evidence_missing} cite evidence that is not on disk.{review.capped ? ` ${review.capped} failed tests are capped at 60.` : ""}{review.tokens?.total ? ` Review used ${review.tokens.total} tokens (${review.tokens.review} reviewing, ${review.tokens.revise} revising).` : ""}</p>}
      {review.records?.length > 0 ? <CaseTable records={review.records} /> : review.issues?.length > 0 && <ul className="mt-1 list-disc pl-5 text-xs text-slate-600 dark:text-slate-400">{review.issues.slice(0, 8).map((issue: string, i: number) => <li key={i}>{issue}</li>)}</ul>}
    </div>
  );
}
