import { Upload } from "lucide-react";
import { Badge, Card } from "../../components/ui";
import { getFileBadgeTone } from "./lib";

type Props = { safeSources: any[]; selected: string[]; setSelected: (v: string[]) => void; onUpload: (file?: File) => void };

export function SourcesCard({ safeSources, selected, setSelected, onUpload }: Props) {
  return (
    <Card title="Source documents">
      <label className="mb-2 inline-flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-indigo-500 hover:underline">
        <Upload className="h-3.5 w-3.5" /> Upload (.md, .txt, .pdf, .docx, .xlsx)
        <input
          type="file"
          name="source-file"
          accept=".md,.txt,.pdf,.docx,.doc,.xlsx,.pptx,.ppt,.csv,.json,.yaml,.yml"
          className="hidden"
          onChange={(e) => onUpload(e.target.files?.[0])}
        />
      </label>
      {safeSources.length ? (
        <ul className="space-y-1.5 text-xs">
          {safeSources.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-1 rounded-lg border border-slate-100 bg-white p-1.5 dark:border-slate-800 dark:bg-slate-900/60">
              <label className="flex items-center gap-2 truncate cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.includes(s.id)}
                  onChange={(e) =>
                    setSelected(e.target.checked ? [...selected, s.id] : selected.filter((x) => x !== s.id))
                  }
                />
                <span className="truncate font-medium text-slate-700 dark:text-slate-300" title={s.filename}>
                  {s.filename}
                </span>
              </label>
              <Badge tone={getFileBadgeTone(s.filename)}>
                {s.filename.split(".").pop()?.toUpperCase() || "FILE"}
              </Badge>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-500">None uploaded.</p>
      )}
    </Card>
  );
}
