"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useToast } from "../../components/ui";

export function useDocuments(project: any) {
  const router = useRouter();
  const toast = useToast();
  const [docs, setDocs] = useState<any[] | null>(null);
  const [kind, setKind] = useState("");
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [template, setTemplate] = useState("builtin_brd");
  const [templates, setTemplates] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [docToDelete, setDocToDelete] = useState<any>(null);

  const fetchDocs = useCallback(() => {
    // Strictly project-scoped document fetch
    api(`/projects/${project.id}/documents`)
      .then((res) => {
        const list = Array.isArray(res) ? res : [];
        // Strict project-id isolation safeguard
        const scoped = list.filter((d) => !d.project_id || d.project_id === project.id);
        setDocs(scoped);
      })
      .catch(() => setDocs([]));
  }, [project.id]);

  useEffect(() => {
    fetchDocs();

    api(`/templates?project_id=${project.id}`)
      .then((res) => setTemplates(Array.isArray(res) ? res : []))
      .catch(() => setTemplates([]));
  }, [project.id, fetchDocs]);

  const executeDeleteDoc = async () => {
    if (!docToDelete) return;
    try {
      await api(`/documents/${docToDelete.id}`, { method: "DELETE" });
      toast("Document deleted successfully");
      setDocToDelete(null);
      fetchDocs();
    } catch (e: any) {
      setError(e.message || "Failed to delete document");
    }
  };

  const safeTemplates = Array.isArray(templates) ? templates : [];
  const create = async () => {
    try {
      const t = safeTemplates.find((x) => x?.id === template);
      const doc = await api(`/projects/${project.id}/documents`, {
        json: { title, kind: t?.kind || "brd", template_id: template },
      });
      router.push(`/projects/${project.id}/documents/${doc.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return { docs, kind, setKind, query, setQuery, title, setTitle, template, setTemplate, safeTemplates, error, docToDelete, setDocToDelete, executeDeleteDoc, create };
}
