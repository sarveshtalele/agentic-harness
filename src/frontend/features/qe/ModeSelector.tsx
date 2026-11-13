import { Building2, Sprout } from "lucide-react";

export function ModeSelector({ projectMode, setProjectMode }: { projectMode: "brownfield" | "greenfield"; setProjectMode: (m: "brownfield" | "greenfield") => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xs dark:border-slate-800 dark:bg-[#0b1329]">
      <div className="flex items-center gap-3">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
          Lifecycle Strategy:
        </span>
        <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <button
            type="button"
            onClick={() => setProjectMode("brownfield")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              projectMode === "brownfield"
                ? "bg-white text-indigo-700 shadow-sm dark:bg-indigo-950 dark:text-indigo-300 border border-slate-200 dark:border-indigo-800"
                : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-300"
            }`}
          >
            <Building2 className="h-3.5 w-3.5" />
            <span>Brownfield (existing repository)</span>
          </button>
          <button
            type="button"
            onClick={() => setProjectMode("greenfield")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              projectMode === "greenfield"
                ? "bg-white text-emerald-700 shadow-sm dark:bg-emerald-950 dark:text-emerald-300 border border-slate-200 dark:border-emerald-800"
                : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-300"
            }`}
          >
            <Sprout className="h-3.5 w-3.5" />
            <span>Greenfield (new application from the requirements)</span>
          </button>
        </div>
      </div>
      <span className="text-xs text-slate-500 font-medium">
        {projectMode === "brownfield" ? "Reads the existing code in the project's workspace with static analysis" : "Builds the application, its tests and runners from the approved requirements"}
      </span>
    </div>
  );
}
