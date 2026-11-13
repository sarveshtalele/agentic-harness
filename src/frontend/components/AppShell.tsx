"use client";

import { Activity, BarChart3, BookOpen, House, ChevronLeft, ChevronRight, Cpu, UsersRound, Bot, Sparkles, CheckSquare, FileText, FolderKanban, ListTree, Settings, ShieldCheck, Terminal, Wand2 } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useFeatures } from "../lib/features";
import { useAuth, UserMenu } from "./AuthGate";
import { ThemeToggle } from "./ui";

interface NavSection {
  title: string;
  items: Array<{
    href: string;
    label: string;
    icon: any;
    admin?: boolean;
    badge?: boolean;
    feature?: string; // hidden when the member lacks this feature (R2)
  }>;
}

const navSections: NavSection[] = [
  {
    title: "WORKSPACE & AGENTS",
    items: [
      { href: "/home", label: "Home", icon: House },
      { href: "/projects", label: "Projects", icon: FolderKanban },
      { href: "/harness", label: "Autonomous QE Harness", icon: Terminal, feature: "harness" },
      { href: "/approvals", label: "Gate Approvals", icon: CheckSquare, badge: true },
      { href: "/agents", label: "AI Specialist Roster", icon: Bot },
    ],
  },
  {
    title: "STUDIOS & ECOSYSTEM",
    items: [
      { href: "/skills/studio", label: "Skill Creator Studio", icon: Wand2, feature: "skills" },
      { href: "/skills", label: "Project Skills & Tools", icon: Sparkles },
      { href: "/mcp", label: "MCP Server Registry", icon: Cpu, feature: "mcp" },
      { href: "/templates", label: "Specification Templates", icon: FileText, feature: "docs" },
    ],
  },
  {
    title: "GOVERNANCE & INSIGHTS",
    items: [
      { href: "/observability", label: "Observability & Telemetry", icon: Activity, feature: "traces" },
      { href: "/traces", label: "Trace Explorer", icon: ListTree, feature: "traces" },
      { href: "/capabilities", label: "Capability Registry", icon: Cpu },
      { href: "/docs", label: "Platform Documentation", icon: BookOpen },
    ],
  },
  {
    title: "ENTERPRISE ADMIN",
    items: [
      { href: "/users", label: "User Access & Accounts", icon: UsersRound, admin: true },
      { href: "/usage", label: "Token Budget & Usage", icon: BarChart3, admin: true, feature: "usage" },
      { href: "/settings", label: "System Configuration", icon: Settings, admin: true },
    ],
  },
];

/** Workspace frame for pages outside a project: brand and left navigation with collapsible icon-only mode. */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const features = useFeatures();
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
            <Link href="/home" className="flex items-center gap-2.5 px-1">
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
        <nav aria-label="Workspace" className="flex-1 space-y-3 overflow-y-auto pr-1">
          {(() => {
            const allHrefs = navSections.flatMap((s) => s.items.map((i) => i.href));
            const activeHref = allHrefs
              .filter((h) => (h === "/" ? pathname === "/" : pathname === h || pathname.startsWith(h + "/")))
              .sort((a, b) => b.length - a.length)[0] || (pathname === "/" ? "/" : "");

            return navSections.map((sec, secIdx) => {
              // inside a project the Studio is out of place: skills are made for the whole platform, not for one project
              const inProject = pathname.startsWith("/projects/");
              const visibleItems = sec.items.filter((item) => (!item.admin || user?.role === "admin") && (!item.feature || !!features?.includes(item.feature)) && !(inProject && item.href === "/skills/studio"));
              if (visibleItems.length === 0) return null;
              return (
                <div key={sec.title || secIdx} className="space-y-0.5">
                  {!collapsed && (
                    <div className="px-2.5 pt-1.5 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                      {sec.title}
                    </div>
                  )}
                  {visibleItems.map((item) => {
                    const active = item.href === activeHref;
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        title={item.label}
                        aria-current={active ? "page" : undefined}
                        className={`flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition ${
                          active
                            ? "bg-indigo-600 text-white font-semibold shadow-sm"
                            : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-900"
                        } ${collapsed ? "justify-center" : ""}`}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                        {!collapsed && item.badge && pending > 0 && (
                          <span data-testid="approvals-badge" className="rounded-full bg-amber-500 px-1.5 text-[11px] font-bold text-slate-950">
                            {pending}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              );
            });
          })()}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-6 py-2.5 backdrop-blur dark:border-slate-800 dark:bg-[#060a17]/90">
          {pathname === "/harness" ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-600 text-white shadow-xs">
                <Terminal className="h-3.5 w-3.5" />
              </span>
              <span className="font-bold text-slate-800 dark:text-slate-100">Autonomous QE Harness</span>
              <span className="hidden sm:inline-block rounded-md bg-indigo-500/10 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                Microsoft Agent Framework
              </span>
            </div>
          ) : (
            <Link href="/harness" className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:text-indigo-300 transition">
              <Terminal className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>QE Harness</span>
              <span className="rounded bg-indigo-600/20 px-1 py-0.2 text-[10px] font-mono">Enterprise QE</span>
            </Link>
          )}
          <div className="flex items-center gap-3">
            <UserMenu />
            <ThemeToggle />
          </div>
        </header>
        <main className={`mx-auto p-6 ${pathname === "/harness" ? "max-w-full px-4 py-3" : "max-w-6xl"}`}>
          {(user as any)?.warnings?.map((w: string) => <p key={w} role="alert" data-testid="admin-warning" className="mb-4 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">{w}</p>)}
          {children}
        </main>
      </div>
    </div>
  );
}
