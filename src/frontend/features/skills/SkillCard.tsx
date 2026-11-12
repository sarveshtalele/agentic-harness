import { Terminal, Trash2 } from "lucide-react";
import { SkillItem } from "./lib";

export function SkillCard({ s, onOpen, onDelete, onRecheck }: { s: SkillItem; onOpen: () => void; onDelete?: (e: React.MouseEvent) => void; onRecheck?: (e: React.MouseEvent) => void }) {
  return (
    <div
          data-testid="skill-card"
      onClick={() => onOpen()}
      className="group relative flex cursor-pointer flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 transition-all hover:border-indigo-500 hover:shadow-md dark:border-slate-800 dark:bg-[#0b1329]"
    >
      <div>
        {/* Header: name, version and content hash */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
              <Terminal className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-900 group-hover:text-indigo-600 dark:text-slate-100 dark:group-hover:text-indigo-400 transition">
                {s.name}
              </h3>
              <span className="text-[11px] text-slate-400">
                {s.version ? `v${s.version}` : "unversioned"}
              </span>
            </div>
          </div>

          {/* Real facts only: the content hash MAF loaded; no security score until a scanner runs (plan P6) */}
          <div className="flex flex-col items-end">
            <span className="mono rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300" title="SHA-256 of the skill body and references">
              {s.sha256?.slice(0, 10)}
            </span>
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold mt-0.5">Security scan: not run</span>
          </div>
        </div>

        {s.health && s.health.verdict !== "ok" && (
          <div
            data-testid="skill-health"
            role="status"
            title={s.health.reason}
            className={`mt-3 rounded-lg border px-2 py-1.5 text-[11px] leading-snug ${s.health.verdict === "flagged"
              ? "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
              : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300"}`}
          >
            <span className="font-semibold">{s.health.verdict === "flagged" ? "Flagged: cannot run here" : "Warning"}</span>
            <span className="block break-words">{s.health.reason}</span>
            {onRecheck && (
              <button type="button" onClick={onRecheck} className="mt-1 font-semibold underline underline-offset-2">
                Check again
              </button>
            )}
          </div>
        )}

        {/* Description */}
        <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400 line-clamp-3">
          {s.description}
        </p>

        <div className="mt-4 grid grid-cols-2 gap-1.5 rounded-lg border border-slate-100 bg-slate-50/50 p-2 text-center dark:border-slate-800/60 dark:bg-slate-900/40">
          <div>
            <span className="block text-[11px] font-bold text-slate-700 dark:text-slate-300">{s.references.length}</span>
            <span className="block text-[9px] text-slate-400">References</span>
          </div>
          <div>
            <span className="block text-[11px] font-bold text-slate-700 dark:text-slate-300">{s.chars.toLocaleString()}</span>
            <span className="block text-[9px] text-slate-400">Characters</span>
          </div>
        </div>
      </div>

      {/* Footer: Agents & Chars */}
      <div className="mt-4 border-t border-slate-100 pt-3 dark:border-slate-800/60 flex items-center justify-between text-[11px]">
        <div className="flex flex-wrap gap-1">
          {s.agents.length > 0 ? (
            s.agents.map((a: string) => (
              <span
                key={a}
                className="rounded bg-indigo-50/80 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
              >
                {a}
              </span>
            ))
          ) : (
            <span className="text-slate-400">Universal skill</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400 font-mono text-[10px]">
            {s.chars.toLocaleString()} chars
          </span>
          {onDelete && <button
            type="button"
            onClick={(e) => onDelete(e)}
            className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition cursor-pointer"
            title={`Delete ${s.name}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>}
        </div>
      </div>
    </div>
  );
}
