"use client";

import { Trash2 } from "lucide-react";
import { useMemo } from "react";
import { tableRows, tableText } from "./blocks";

export function TableBlock({ raw, gherkin, label, readOnly, onChange }: { raw: string; gherkin: boolean; label: string; readOnly: boolean; onChange: (raw: string) => void }) {
  const rows = useMemo(() => {
    const parsed = tableRows(raw, gherkin);
    const width = Math.max(...parsed.map((row) => row.length));
    return parsed.map((row) => [...row, ...Array(width - row.length).fill("")]);
  }, [raw, gherkin]);
  const indent = raw.match(/^\s*/)?.[0] || "";
  const commit = (next: string[][]) => onChange(tableText(next, gherkin, indent));
  const setCell = (r: number, c: number, value: string) => commit(rows.map((row, i) => (i === r ? row.map((v, j) => (j === c ? value : v)) : row)));
  if (readOnly) {
    return (
      <div className="doc-table-wrap w-full max-w-full overflow-x-auto">
        <table className="doc-table w-full max-w-full">
          <thead>
            <tr>
              {rows[0].map((v, c) => (
                <th key={c} className="break-words">
                  {v}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(1).map((row, r) => (
              <tr key={r}>
                {row.map((v, c) => (
                  <td key={c} className="break-all">
                    {v}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  const button = "rounded border border-slate-300 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600 hover:border-indigo-500 hover:text-indigo-500 dark:border-slate-700 dark:text-slate-400";
  return (
    <div data-testid="table-block">
      <div className="doc-table-wrap w-full max-w-full overflow-x-auto">
        <table className="doc-table w-full max-w-full">
          <tbody>
            {rows.map((row, r) => (
              <tr key={r} className={r === 0 ? "doc-table-head" : ""}>
                {row.map((value, c) => (
                  <td key={c} className="break-all">
                    <textarea
                      rows={1}
                      aria-label={`${label}, row ${r + 1}, column ${c + 1}`}
                      className="doc-cell break-all"
                      value={value}
                      onChange={(e) => setCell(r, c, e.target.value.replace(/\s*\n\s*/g, " "))}
                    />
                  </td>
                ))}
                <td className="w-6 !border-0 !bg-transparent !p-0">
                  {r > 0 && rows.length > 2 && (
                    <button
                      type="button"
                      aria-label={`Remove row ${r + 1}`}
                      title="Remove row"
                      className="ml-1 text-slate-400 hover:text-rose-500"
                      onClick={() => commit(rows.filter((_, i) => i !== r))}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-1 flex flex-wrap gap-1.5">
        <button type="button" className={button} onClick={() => commit([...rows, rows[0].map(() => "")])}>Add row</button>
        <button type="button" className={button} onClick={() => commit(rows.map((row, r) => [...row, r === 0 ? `Column ${row.length + 1}` : ""]))}>Add column</button>
        {rows[0].length > 1 && <button type="button" className={button} onClick={() => commit(rows.map((row) => row.slice(0, -1)))}>Remove last column</button>}
      </div>
    </div>
  );
}
