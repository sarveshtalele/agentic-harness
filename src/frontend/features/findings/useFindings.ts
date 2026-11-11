"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";

/** Loads the open findings, and picks the active or latest scan or change run on mount. */
export function useFindings(projectId: string, runId: string | null, setRunId: (id: string | null) => void) {
  const [findings, setFindings] = useState<any[]>([]);
  const load = useCallback(() => {
    api(`/projects/${projectId}/findings`)
      .then((res) => setFindings(Array.isArray(res) ? res : []))
      .catch(() => setFindings([]));
  }, [projectId]);

  // Check for active running workflows on mount to prevent lost memory
  useEffect(() => {
    load();
    api(`/projects/${projectId}/runs`)
      .then((runs) => {
        if (Array.isArray(runs)) {
          const active = runs.find(
            (r: any) =>
              ["bug_scan", "change"].includes(r?.workflow) &&
              ["running", "waiting_approval"].includes(r?.status)
          );
          if (active) {
            setRunId(active.id);
          } else if (!runId) {
            const latest = runs.find((r: any) => ["bug_scan", "change"].includes(r?.workflow));
            if (latest) {
              setRunId(latest.id);
            }
          }
        }
      })
      .catch(() => {});
  }, [load, projectId]);

  return { findings, load };
}
