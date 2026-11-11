type Tab = "document" | "scenarios" | "source" | "history";

export function DocumentTabs({ tab, setTab, hasGherkin, versionCount }: { tab: Tab; setTab: (t: Tab) => void; hasGherkin: boolean; versionCount: number }) {
  return (
    <div role="tablist" className="mb-3 flex gap-1 border-b border-slate-200 dark:border-slate-800">
      {(["document", ...(hasGherkin ? ["scenarios"] : []), "source", "history"] as const).map((t) => (
        <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t as any)} className={`border-b-2 px-3 py-1.5 text-sm font-semibold capitalize ${tab === t ? "border-indigo-500 text-indigo-500" : "border-transparent text-slate-500 hover:text-slate-300"}`}>{t === "scenarios" ? "Gherkin Scenarios" : t}{t === "history" ? ` (${versionCount})` : ""}</button>
      ))}
    </div>
  );
}
