import { Loader2 } from "lucide-react";
import { ReactNode } from "react";

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-8 text-center">
      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</p>
      {children && <div className="mt-2 text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <p className="flex items-center gap-2 p-4 text-sm text-slate-500">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </p>
  );
}
