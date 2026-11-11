"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, ErrorNote, Field, inputClass, Spinner } from "../../components/ui";
import { api, upload } from "../../lib/api";

export function NewProject({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const project = await api("/projects", { json: { name, description } });
      try {
        if (url.trim()) await api(`/projects/${project.id}/repo/git`, { json: { url: url.trim() } });
        else if (file) {
          const form = new FormData();
          form.append("file", file);
          await upload(`/projects/${project.id}/repo/zip`, form);
        }
      } catch (err: any) {
        router.push(`/projects/${project.id}/repository?error=${encodeURIComponent(err.message)}`);
        return;
      }
      onCreated();
      onClose();
      router.push(`/projects/${project.id}`); // open the new project, as its overview shows the next step
    } catch (err: any) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="New project"
    >
      <form
        onSubmit={submit}
        className="w-full max-w-lg space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0b1329]"
      >
        <h2 className="text-lg font-bold">New project</h2>
        <Field label="Name">
          <input
            required
            autoFocus
            maxLength={120}
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="Description">
          <textarea
            className={inputClass}
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <Field
          label="Git URL (optional)"
          hint="Public HTTPS URL or owner/repo. For private repositories, add a connection in Settings, then use the Repository page."
        >
          <input
            className={inputClass}
            placeholder="https://github.com/owner/repo"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={!!file}
          />
        </Field>
        <Field label="Or upload a ZIP (optional)">
          <input
            type="file"
            accept=".zip"
            className={inputClass}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={!!url}
          />
        </Field>
        <ErrorNote message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner /> : "Create project"}
          </Button>
        </div>
      </form>
    </div>
  );
}

