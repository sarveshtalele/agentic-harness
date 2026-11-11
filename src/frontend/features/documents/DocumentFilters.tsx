import { inputClass } from "../../components/ui";

type Props = { query: string; setQuery: (v: string) => void; kind: string; setKind: (v: string) => void; kinds: string[]; shownCount: number; total: number };

export function DocumentFilters({ query, setQuery, kind, setKind, kinds, shownCount, total }: Props) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Search documents"
          className={`${inputClass} max-w-xs`}
          placeholder="Search by title..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          aria-label="Filter by kind"
          className={`${inputClass} max-w-[180px]`}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="">All Document Kinds</option>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {k.toUpperCase()}
            </option>
          ))}
        </select>
      </div>
      <span className="text-xs text-slate-500 font-medium">
        Showing {shownCount} of {total} project documents
      </span>
    </div>
  );
}
