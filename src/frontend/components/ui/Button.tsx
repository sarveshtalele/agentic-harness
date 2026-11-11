import { Loader2 } from "lucide-react";

const variants = {
  primary: "bg-indigo-600 hover:bg-indigo-500 text-white",
  secondary: "border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800",
  danger: "border border-rose-500/50 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10",
  success: "bg-emerald-600 hover:bg-emerald-500 text-white",
};

export function Button({ variant = "primary", busy, children, className = "", ...props }: { variant?: keyof typeof variants; busy?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button {...props} disabled={props.disabled || busy} className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}>
      {busy && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
