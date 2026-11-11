"use client";

import { ImagePlus, Table2, Type } from "lucide-react";
import { upload } from "../../../lib/api";

export function Insert({ documentId, onInsert, onError }: { documentId: string; onInsert: (raw: string) => void; onError: (message: string) => void }) {
  const button = "inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-600 hover:border-indigo-500 hover:text-indigo-500 dark:border-slate-700 dark:bg-[#0b1329] dark:text-slate-300";
  const addImage = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const saved = await upload(`/documents/${documentId}/images`, form);
      onInsert(`![${file.name.replace(/[[\]]/g, "")}](${saved.url})`);
    } catch (e: any) {
      onError(e.message);
    }
  };
  return (
    <>
      <button type="button" className={button} onClick={() => onInsert("New text. Select it to edit.")}><Type className="h-3.5 w-3.5" /> Add text</button>
      <button type="button" className={button} onClick={() => onInsert("| Column 1 | Column 2 |\n| --- | --- |\n|  |  |")}><Table2 className="h-3.5 w-3.5" /> Add table</button>
      <label className={`${button} cursor-pointer`}><ImagePlus className="h-3.5 w-3.5" /> Add image<input aria-label="Add image" type="file" accept="image/png,image/jpeg,image/gif,image/webp" className="sr-only" onChange={(e) => { addImage(e.target.files?.[0]); e.target.value = ""; }} /></label>
    </>
  );
}
