import { Search, Sliders } from "lucide-react";

export function SkillFilters({ search, setSearch, selectedAgent, setSelectedAgent, allAgents, total }: { search: string; setSearch: (v: string) => void; selectedAgent: string; setSelectedAgent: (v: string) => void; allAgents: string[]; total: number }) {
  return (
  <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div className="relative flex-1">
      <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
      <input
        type="text"
        placeholder="Search skills by name, description, or capability..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
      />
    </div>
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 flex items-center gap-1">
        <Sliders className="h-3.5 w-3.5" /> Agent:
      </span>
      <select
        value={selectedAgent}
        onChange={(e) => setSelectedAgent(e.target.value)}
        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium outline-none transition focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
      >
        <option value="all">All Specialist Agents ({total})</option>
        {allAgents.map(a => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>
    </div>
  </div>
  );
}
