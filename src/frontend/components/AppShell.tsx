"use client";

import { Activity, BarChart3, BookOpen, ChevronLeft, ChevronRight, Cpu, UsersRound, Bot, Sparkles, CheckSquare, FileText, FolderKanban, Settings, ShieldCheck, Terminal } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth, UserMenu } from "./AuthGate";
import { ThemeToggle } from "./ui";

const nav = [
  { href: "/", label: "Projects", icon: FolderKanban },
  { href: "/harness", label: "QE Harness", icon: Terminal },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/skills", label: "Skills", icon: Sparkles },
  { href: "/mcp", label: "MCP Servers", icon: Cpu },
  { href: "/observability", label: "Observability", icon: Activity },
  { href: "/templates", label: "Templates", icon: FileText },
  { href: "/docs", label: "Documentation", icon: BookOpen },
  { href: "/users", label: "Users", icon: UsersRound, admin: true },
  { href: "/usage", label: "Usage", icon: BarChart3, admin: true },
  { href: "/settings", label: "Settings", icon: Settings, admin: true },
];

/** Workspace frame for pages outside a project: brand and left navigation with collapsible icon-only mode. */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const links = nav.filter((item) => !item.admin || user?.role === "admin");
  const [pending, setPending] = useState(0);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const load = () => api("/approvals").then((items) => setPending(items.length)).catch(() => {});
    load();
    const timer = setInterval(load, 10_000);
    return () => clearInterval(timer);
  }, [pathname]);

  return (
    <div className="flex min-h-screen">
      <aside className={`sticky top-0 flex h-screen shrink-0 flex-col border-r border-slate-200 bg-white p-3 transition-all dark:border-slate-800 dark:bg-[#060a17] ${collapsed ? "w-16" : "w-60"}`}>
        <div className="mb-4 flex items-center justify-between border-b border-slate-200 pb-3 dark:border-slate-800">
          {!collapsed && (
            <Link href="/" className="flex items-center gap-2.5 px-1">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white"><ShieldCheck className="h-4 w-4" /></span>
              <span className="text-base font-bold">Agentic QE Platform</span>
            </Link>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="rounded-md border border-slate-200 p-1 text-slate-500 hover:bg-slate-100 dark:border-slate-800 dark:hover:bg-slate-800"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>
        <nav aria-label="Workspace" className="flex-1 space-y-0.5 overflow-y-auto">
          {links.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-semibold transition ${
                  active ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-900"
                } ${collapsed ? "justify-center" : ""}`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="flex-1">{item.label}</span>}
                {!collapsed && item.href === "/approvals" && pending > 0 && (
                  <span data-testid="approvals-badge" className="rounded-full bg-amber-500 px-1.5 text-[11px] font-bold text-slate-950">
                    {pending}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-6 py-2.5 backdrop-blur dark:border-slate-800 dark:bg-[#060a17]/90">
          <Link href="/harness" className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:text-indigo-300">
            <Terminal className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>QE Harness</span>
            <span className="rounded bg-indigo-600/20 px-1 py-0.2 text-[10px] font-mono">MAF 2.0</span>
          </Link>
          <div className="flex items-center gap-3">
            <UserMenu />
            <ThemeToggle />
          </div>
        </header>
        <main className={`mx-auto p-6 ${pathname === "/harness" ? "max-w-full px-4 py-3" : "max-w-6xl"}`}>{children}</main>
      </div>
    </div>
  );
}
