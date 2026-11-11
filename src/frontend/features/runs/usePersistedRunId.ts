"use client";

import { useState } from "react";

/** The active run id, kept across tab switches in local and session storage. */
export function usePersistedRunId(key: string) {
  const [runId, setRunIdState] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(key) || sessionStorage.getItem(key) || null;
    }
    return null;
  });

  const setRunId = (id: string | null) => {
    setRunIdState(id);
    if (typeof window !== "undefined") {
      if (id) {
        localStorage.setItem(key, id);
        sessionStorage.setItem(key, id);
      } else {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
      }
    }
  };

  return [runId, setRunId] as const;
}
