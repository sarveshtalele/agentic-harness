import Link from "next/link";

export function StatsRow({ stats }: { stats: [string, number, any, string, string][] }) {
  return (
    <dl className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
      {stats.map(([label, value, Icon, href, id]) => (
        <Link
          key={label}
          href={href}
          data-testid={`stat-${id}`}
          className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 hover:border-indigo-500/60 dark:border-slate-800 dark:bg-[#0b1329]"
        >
          <Icon
            className={`h-5 w-5 ${
              id === "need-approval" && value > 0 ? "text-amber-500" : "text-indigo-500"
            }`}
          />
          <span>
            <dd className="text-xl font-bold leading-tight">{value}</dd>
            <dt className="text-xs text-slate-500">{label}</dt>
          </span>
        </Link>
      ))}
    </dl>
  );
}
