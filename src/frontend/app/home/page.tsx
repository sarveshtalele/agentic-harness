"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, CheckSquare, ChevronRight, Cpu, FileText, FolderKanban, Wand2 } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { useAuth } from "../../components/AuthGate";
import { Card, Empty, ErrorNote, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useFeatures } from "../../lib/features";

// Tiles for features that have a page today; BA Studio joins with R3. A tile without a feature is for everyone.
const TILES = [
  { href: "/projects", label: "QE cycle", icon: FolderKanban, feature: "qe" },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/skills/studio", label: "Skill Studio", icon: Wand2, feature: "skills" },
  { href: "/mcp", label: "MCP", icon: Cpu, feature: "mcp" },
  { href: "/templates", label: "Documents", icon: FileText, feature: "docs" },
  { href: "/traces", label: "Traces", icon: Activity, feature: "traces" },
];

/** Home after sign-in (plan 12.2): where you left off and your work. */
export default function HomePage() {
  const { user } = useAuth();
  const features = useFeatures();
  const [projects, setProjects] = useState<any[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/projects").then(setProjects).catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <PageTitle title="Home" subtitle={user ? `Signed in as ${user.username}` : undefined} />
      <ErrorNote message={error} />
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <Card title="Continue where you left off">
            {!projects ? <Spinner label="Loading projects" /> : !projects.length ? (
              <Empty title="No projects yet"><Link href="/projects" className="underline">Create or join a project.</Link></Empty>
            ) : (
              <ul className="divide-y divide-slate-200 dark:divide-slate-800" data-testid="home-recent">
                {projects.slice(0, 5).map((p) => (
                  <li key={p.id}>
                    <Link href={`/projects/${p.id}`} className="flex items-center justify-between gap-3 py-2 hover:text-indigo-600">
                      <span className="font-medium">{p.name}</span>
                      <span className="flex items-center gap-1 text-xs text-slate-500">
                        {p.pending ? `${p.pending} waiting for a decision` : `${p.gates_approved || 0} gates signed`}
                        <ChevronRight className="h-3.5 w-3.5" />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Your work">
            {!features ? <Spinner label="Loading your access" /> : (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="home-tiles">
                {TILES.filter((t) => !t.feature || features.includes(t.feature)).map(({ href, label, icon: Icon }) => (
                  <Link key={href + label} href={href} className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm font-medium hover:border-indigo-400 dark:border-slate-800">
                    <Icon className="h-4 w-4 text-indigo-500" /> {label}
                  </Link>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
