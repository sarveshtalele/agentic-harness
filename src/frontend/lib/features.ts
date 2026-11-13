"use client";

import { useEffect, useState } from "react";
import { api } from "./api";

/** The signed-in member's features (R2): null while loading. The server enforces them; the UI only hides what is denied. */
export function useFeatures(): string[] | null {
  const [features, setFeatures] = useState<string[] | null>(null);
  useEffect(() => {
    api("/features/me").then((r) => setFeatures(r.features)).catch(() => setFeatures([]));
  }, []);
  return features;
}
