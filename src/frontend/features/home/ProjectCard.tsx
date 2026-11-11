import { Archive, FolderGit2, Pencil, Terminal, Trash2, Undo2 } from "lucide-react";
import Link from "next/link";
import { Badge } from "../../components/ui";
import { when } from "../../lib/api";

export function ProjectCard({ p, archived, onRename, onArchive, onRemove }: { p: any; archived: boolean; onRename: () => void; onArchive: () => void; onRemove: () => void }) {
  return (
    <article
          className="group flex flex-col rounded-xl border border-slate-200 bg-white p-4 transition hover:border-indigo-500/60 dark:border-slate-800 dark:bg-[#0b1329]"
      data-testid="project-card"
    >
      <div className="flex items-start justify-between gap-2">
        <Link href={`/projects/${p.id}`} className="flex-1 truncate">
          <h2 className="truncate font-bold hover:text-indigo-600 transition">{p.name}</h2>
        </Link>
        <Link
          href={`/harness?project=${p.id}`}
          title="Launch in QE Harness"
          className="flex items-center gap-1 rounded bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-600 hover:bg-indigo-600 hover:text-white dark:bg-indigo-950/60 dark:text-indigo-400 dark:hover:bg-indigo-600 dark:hover:text-white transition"
        >
          <Terminal className="h-3 w-3" />
          <span>Harness</span>
        </Link>
      </div>

      <p className="mt-1 line-clamp-2 min-h-8 text-xs text-slate-600 dark:text-slate-400">
        {p.description || "No description"}
      </p>

      <p className="mt-3 flex items-center gap-1.5 truncate text-xs text-slate-600 dark:text-slate-400">
        <FolderGit2 className="h-3.5 w-3.5 shrink-0" /> {p.repo ? p.repo.url : "No repository"}
      </p>

      {p.repo?.languages?.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {p.repo.languages.map((l: string) => (
            <Badge key={l} tone="indigo">
              {l}
            </Badge>
          ))}
        </div>
      )}

      <dl className="mt-3 grid grid-cols-4 gap-1 text-center text-xs">
        {[
          ["Gates", `${p.gates_approved}/6`, "governance"],
          ["Docs", p.documents, "documents"],
          ["Runs", p.runs, "runs"],
          ["Bugs", p.findings, "bugs"],
        ].map(([label, value, tab]) => (
          <Link
            key={label as string}
            href={`/projects/${p.id}/${tab}`}
            data-testid={`card-${tab}`}
            className="rounded-lg bg-slate-100 py-1 hover:ring-1 hover:ring-indigo-500 dark:bg-slate-900"
          >
            <dd className="font-bold">{value}</dd>
            <dt className="text-[10px] text-slate-500">{label}</dt>
          </Link>
        ))}
      </dl>

      <footer className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
        <span>
          {p.pending > 0 ? (
            <Link href="/approvals">
              <Badge tone="amber">{`${p.pending} awaiting approval`}</Badge>
            </Link>
          ) : (
            `Updated ${when(p.updated_at)}`
          )}
        </span>
        <span className="flex gap-1.5">
          <button
            aria-label={`Rename ${p.name}`}
            title="Rename"
            onClick={() => onRename()}
            className="hover:text-indigo-500"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            aria-label={archived ? `Restore ${p.name}` : `Archive ${p.name}`}
            title={archived ? "Restore" : "Archive"}
            onClick={() => onArchive()}
            className="hover:text-indigo-500"
          >
            {archived ? <Undo2 className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
          </button>
          <button
            aria-label={`Delete ${p.name}`}
            title="Delete"
            onClick={() => onRemove()}
            className="hover:text-rose-500"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </span>
      </footer>
    </article>
  );
}
