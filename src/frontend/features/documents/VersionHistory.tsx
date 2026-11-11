import { RotateCcw } from "lucide-react";
import { Card } from "../../components/ui";
import { api, when } from "../../lib/api";

type Props = { versions: any[]; viewing: any; diff: any; docId: string; setViewing: (v: any) => void; setDiff: (v: any) => void; restore: (version: number) => void };

export function VersionHistory({ versions, viewing, diff, docId, setViewing, setDiff, restore }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-[360px_1fr] [&>*]:min-w-0">
      <Card>
        <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
          {versions.map((v, i) => (
            <li key={v.version} className="py-2">
              <div className="flex items-center justify-between"><b>v{v.version}</b><span className="text-xs text-slate-500">{when(v.created_at)}</span></div>
              <p className="truncate text-xs text-slate-500" title={v.note}>{v.author_name} · {v.note}</p>
              <div className="mt-1 flex gap-3 text-xs">
                <button className="text-indigo-500" onClick={async () => { setViewing(await api(`/documents/${docId}?version=${v.version}`)); setDiff(""); }}>View</button>
                {i < versions.length - 1 && <button className="text-indigo-500" onClick={async () => { setDiff(await api(`/documents/${docId}/diff?a=${versions[i + 1].version}&b=${v.version}`)); setViewing(null); }}>Diff with v{versions[i + 1].version}</button>}
                {i > 0 && <button className="inline-flex items-center gap-0.5 text-indigo-500" onClick={() => restore(v.version)}><RotateCcw className="h-3 w-3" /> Restore</button>}
              </div>
            </li>
          ))}
        </ul>
      </Card>
      <Card>
        {typeof diff === "string" && diff ? <pre className="mono overflow-auto text-xs">{diff.split("\n").map((l, i) => <div key={i} className={l.startsWith("+") ? "text-emerald-500" : l.startsWith("-") ? "text-rose-500" : ""}>{l || " "}</div>)}</pre>
          : viewing ? <pre className="mono overflow-auto whitespace-pre-wrap text-xs">{viewing.content}</pre>
          : <p className="text-sm text-slate-500">Pick a version to view it or compare it.</p>}
      </Card>
    </div>
  );
}
