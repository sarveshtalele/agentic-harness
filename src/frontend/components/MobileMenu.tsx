"use client";

import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";

/** Below 768 px the sidebar is a drawer behind a menu button (UI audit U1); from 768 px it is the usual sticky sidebar. */
export function useMobileMenu(pathname: string) {
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [pathname]); // a link was followed: close the drawer
  const aside = (collapsed: boolean) =>
    `${open ? "fixed inset-y-0 left-0 z-40 flex w-64" : "hidden"} md:sticky md:top-0 md:flex h-screen shrink-0 flex-col border-r border-slate-200 bg-white p-3 transition-all dark:border-slate-800 dark:bg-[#060a17] ${collapsed ? "md:w-16" : "md:w-60"}`;
  const button = (
    <button onClick={() => setOpen(!open)} aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}
      className="rounded-md border border-slate-200 p-1.5 text-slate-600 md:hidden dark:border-slate-800 dark:text-slate-300">
      {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
    </button>
  );
  const backdrop = open ? <div aria-hidden className="fixed inset-0 z-30 bg-slate-950/40 md:hidden" onClick={() => setOpen(false)} /> : null;
  return { aside, button, backdrop };
}
