"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";

type File = { name: string; os: string; arch: string; kind: string; size: number; sha256: string; url: string };
type Manifest = { configured: boolean; version?: string; files: File[]; error?: string };

const label = (f: File) => (f.os === "windows" ? "Windows (MSI)" : `macOS (${f.kind.toUpperCase()}, ${f.arch === "arm64" ? "Apple silicon" : "Intel"})`);

/** Desktop installers from the published manifest only; says so plainly when none are published. */
export function DesktopDownloads() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  useEffect(() => {
    fetch("/api/downloads", { cache: "no-store" }).then((r) => r.json()).then(setManifest).catch(() => setManifest({ configured: false, files: [] }));
  }, []);
  if (!manifest) return null;
  return (
    <section data-testid="desktop-downloads" className="w-full max-w-sm space-y-2 rounded-2xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-[#0b1329]">
      <h2 className="font-semibold">Desktop app{manifest.version ? ` ${manifest.version}` : ""}</h2>
      <p className="text-xs text-slate-500">Runs the whole platform on your computer, including the harness, plugins and local MCP servers.</p>
      {manifest.files.length ? (
        <ul className="space-y-1.5">
          {manifest.files.map((f) => (
            <li key={f.name}>
              <a href={f.url} className="inline-flex items-center gap-1.5 text-indigo-600 underline dark:text-indigo-400"><Download className="h-4 w-4" /> Download for {label(f)}</a>
              <p className="mono break-all text-[10px] text-slate-500">{(f.size / 1e6).toFixed(1)} MB · SHA-256 {f.sha256}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-500">{manifest.error || "No desktop installer is published yet."}</p>
      )}
    </section>
  );
}
