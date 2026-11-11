"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useProject } from "../../components/ProjectShell";
import { ErrorNote, PageTitle, Spinner, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { Connect } from "./Connect";
import { Details } from "./Details";

export function RepositoryPage() {
  return <Suspense fallback={<Spinner />}><Repository /></Suspense>;
}

function Repository() {
  const { project, refresh } = useProject();
  const params = useSearchParams();
  const [repo, setRepo] = useState<any>(undefined);
  const [error, setError] = useState(params.get("error") || "");
  const [busy, setBusy] = useState("");
  const toast = useToast();
  const load = useCallback(() => api(`/projects/${project.id}/repo`).then(setRepo).catch((e) => { setError(e.message); setRepo(null); }), [project.id]);
  useEffect(() => {
    load();
  }, [load]);

  const act = async (label: string, work: () => Promise<any>) => {
    setBusy(label);
    setError("");
    try {
      await work();
      await load();
      refresh();
      toast("Repository scanned");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  };

  if (repo === undefined) return <Spinner />;
  return (
    <>
      <PageTitle title="Repository" subtitle={repo ? "This project's connected repository and its sandbox. All analysis comes from the real files." : "Clone a Git repository or upload a ZIP. All analysis comes from the real files."} />
      <ErrorNote message={error} />
      {repo && <Details repo={repo} project={project} busy={busy} act={act} setRepo={setRepo} refresh={refresh} />}
      {repo ? (
        <details className="mt-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#0b1329]" data-testid="replace-repository">
          <summary className="cursor-pointer text-sm font-semibold">Replace repository</summary>
          <Connect project={project} busy={busy} act={act} />
        </details>
      ) : <Connect project={project} busy={busy} act={act} />}
    </>
  );
}
