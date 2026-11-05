"use client";

import { Terminal } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { Button, Empty, ErrorNote, Spinner } from "../../components/ui";
import { api } from "../../lib/api";

export default function GlobalHarnessRedirect() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hasProjects, setHasProjects] = useState(true);

  useEffect(() => {
    api("/projects")
      .then((projects) => {
        if (projects && projects.length > 0) {
          router.replace(`/projects/${projects[0].id}/harness`);
        } else {
          setHasProjects(false);
          setLoading(false);
        }
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [router]);

  return (
    <AppShell>
      {loading ? (
        <div className="flex h-96 flex-col items-center justify-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg animate-pulse">
            <Terminal className="h-6 w-6" />
          </div>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Opening QE Harness...
          </p>
          <Spinner />
        </div>
      ) : error ? (
        <ErrorNote message={error} />
      ) : !hasProjects ? (
        <Empty title="No projects yet">
          <p className="mb-4">Create a project first to launch the Agentic QE Harness.</p>
          <Button onClick={() => router.push("/")}>Go to Projects</Button>
        </Empty>
      ) : null}
    </AppShell>
  );
}
