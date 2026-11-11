"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";

/** Project documents, plus picking the active or latest qe run on mount. */
export function useQeDocs(projectId: string, runId: string | null, setRunId: (id: string | null) => void) {
  const [docs, setDocs] = useState<any[]>([]);
  const load = useCallback(() => {
    api(`/projects/${projectId}/documents`)
      .then((res) => {
        const list = Array.isArray(res) ? res : [];
        setDocs(list.filter((d) => !d.project_id || d.project_id === projectId));
      })
      .catch(() => setDocs([]));
  }, [projectId]);

  useEffect(() => {
    load();
    api(`/projects/${projectId}/runs`)
      .then((runs) => {
        if (Array.isArray(runs)) {
          const active = runs.find(
            (r: any) =>
              r?.workflow === "qe" &&
              ["running", "waiting_approval"].includes(r?.status)
          );
          if (active) {
            setRunId(active.id);
          } else if (!runId) {
            const latest = runs.find((r: any) => r?.workflow === "qe");
            if (latest) setRunId(latest.id);
          }
        }
      })
      .catch(() => {});
  }, [load, projectId]);

  return { docs, load };
}

/** The selected run, refreshed every few seconds. */
export function useActiveRun(runId: string | null) {
  const [activeRun, setActiveRun] = useState<any>(null);

  useEffect(() => {
    if (!runId) {
      setActiveRun(null);
      return;
    }
    let isMounted = true;
    const fetchRun = () => {
      api(`/runs/${runId}`)
        .then((data) => {
          if (isMounted) setActiveRun(data);
        })
        .catch(() => {});
    };
    fetchRun();
    const interval = setInterval(fetchRun, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [runId]);

  return activeRun;
}
