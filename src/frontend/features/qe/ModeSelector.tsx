import { Building2, Sprout } from "lucide-react";

type Mode = "brownfield" | "greenfield";
const MODES: { id: Mode; label: string; icon: typeof Building2; on: string }[] = [
  { id: "brownfield", label: "Brownfield", icon: Building2, on: "text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 dark:border-indigo-800" },
  { id: "greenfield", label: "Greenfield", icon: Sprout, on: "text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800" },
];

export function ModeSelector({ projectMode, setProjectMode }: { projectMode: Mode; setProjectMode: (m: Mode) => void }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xs sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-[#0b1329]">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Lifecycle strategy</span>
        <div role="group" aria-label="Lifecycle strategy" className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          {MODES.map(({ id, label, icon: Icon, on }) => (
            <button
              key={id}
              type="button"
              aria-pressed={projectMode === id}
              onClick={() => setProjectMode(id)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${projectMode === id ? `bg-white shadow-sm border border-slate-200 ${on}` : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"}`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
      <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
        {projectMode === "brownfield" ? "Existing repository: reads the code in the project's workspace with static analysis." : "New application: builds the application, its tests and runners from the approved requirements."}
      </span>
    </div>
  );
}
