"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";

export function useBaData(projectId: string, runId: string | null) {
  const [templates, setTemplates] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);

  const loadTemplates = useCallback(() => api(`/templates?project_id=${projectId}`).then((res) => setTemplates(Array.isArray(res) ? res : [])).catch(() => setTemplates([])), [projectId]);
  const loadSources = useCallback(() => api(`/projects/${projectId}/sources`).then((res) => setSources(Array.isArray(res) ? res : [])).catch(() => setSources([])), [projectId]);
  const loadDocs = useCallback(() => api(`/projects/${projectId}/documents`).then((items) => setDocs(Array.isArray(items) ? items.filter((d: any) => ["brd", "prd", "stories", "gherkin"].includes(d?.kind)) : [])).catch(() => setDocs([])), [projectId]);
  
  useEffect(() => {
    loadTemplates();
    loadSources();
    loadDocs();
  }, [loadTemplates, loadSources, loadDocs]);

  // Documents refresh when a run is initiated or finished (strictly zero interval polling)
  useEffect(() => {
    if (!runId) return;
    loadDocs();
  }, [runId, loadDocs]);

  return { templates, sources, docs, loadTemplates, loadSources, loadDocs };
}
