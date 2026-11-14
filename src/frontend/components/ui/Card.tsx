import { ReactNode } from "react";

export function Card({ title, actions, children, className = "", id }: { id?: string; title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section id={id} className={`rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0b1329] p-4 ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h2>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
