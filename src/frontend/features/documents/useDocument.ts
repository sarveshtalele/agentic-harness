"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useToast } from "../../components/ui";
import { reopenText } from "./lib";

export function useDocument(docId: string, projectId: string) {
  const router = useRouter();
  const toast = useToast();
  const [doc, setDoc] = useState<any>(null);
  const [draft, setDraft] = useState("");
  const [note, setNote] = useState("");
  const [tab, setTab] = useState<"document" | "scenarios" | "source" | "history">("document");
  const [versions, setVersions] = useState<any[]>([]);
  const [viewing, setViewing] = useState<any>(null);
  const [diff, setDiff] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [working, setWorking] = useState("");
  const [reviewResult, setReviewResult] = useState<any>(null);
  const [refineText, setRefineText] = useState("");

  const load = useCallback(async () => {
    const [d, v] = await Promise.all([api(`/documents/${docId}`), api(`/documents/${docId}/versions`)]);
    setDoc(d);
    setDraft(d?.content || "");
    setVersions(Array.isArray(v) ? v : []);
  }, [docId]);
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);
  const dirty = doc && draft !== doc.content;
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const saved = await api(`/documents/${docId}`, { method: "PUT", json: { content: draft, note: note || "Edited" } });
      setNote("");
      await load();
      toast(saved.reopened?.length ? `Saved as a new version. ${reopenText(saved.reopened)} reopened and need a new approval.` : "Saved as a new version");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const approve = async () => {
    await api(`/documents/${docId}/approve`, { method: "POST" });
    await load();
    toast("Document approved");
  };
  const restore = async (version: number) => {
    const restored = await api(`/documents/${docId}/restore/${version}`, { method: "POST" });
    if (restored.reopened?.length) toast(`${reopenText(restored.reopened)} reopened and need a new approval.`);
    setViewing(null);
    setDiff("");
    await load();
    setTab("document");
    toast(`Restored v${version} as a new version`);
  };
  const remove = async () => {
    try {
      await api(`/documents/${docId}`, { method: "DELETE" });
      router.push(`/projects/${projectId}/documents`);
    } catch (e: any) {
      setError(e.message || "Failed to delete document");
    }
  };
  const review = async () => {
    setWorking("review");
    setError("");
    try {
      setReviewResult(await api(`/documents/${docId}/review`, { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setWorking("");
    }
  };
  const refine = async () => {
    setWorking("refine");
    setError("");
    try {
      await api(`/documents/${docId}/refine`, { json: { instructions: refineText } });
      setRefineText("");
      await load();
      toast("Agent saved a new version");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setWorking("");
    }
  };

  return { doc, draft, setDraft, note, setNote, tab, setTab, versions, viewing, setViewing, diff, setDiff, error, setError, busy, working, reviewResult, refineText, setRefineText, dirty, save, approve, restore, remove, review, refine };
}
