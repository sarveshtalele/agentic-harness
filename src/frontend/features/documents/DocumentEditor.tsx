"use client";

import { Plus } from "lucide-react";
import { useMemo } from "react";
import { Block, joinBlocks, parseBlocks } from "./editor/blocks";
import { Insert } from "./editor/InsertButtons";
import { TableBlock } from "./editor/TableBlock";
import { TextBlock } from "./editor/TextBlock";

/** The formatted document. Unless read-only, each block can be edited where it appears. */
export function DocumentEditor({ documentId, value, gherkin, readOnly = false, onChange, onError = () => {} }: { documentId: string; value: string; gherkin: boolean; readOnly?: boolean; onChange?: (value: string) => void; onError?: (message: string) => void }) {
  const blocks = useMemo(() => parseBlocks(value, gherkin), [value, gherkin]);
  const emit = (next: Block[]) => onChange?.(joinBlocks(next));
  const update = (index: number, raw: string) => emit(blocks.map((block, i) => (i === index ? { ...block, raw } : block)));
  const remove = (index: number) => emit(blocks.filter((_, i) => i !== index));
  const insert = (index: number, raw: string) => {
    const next = [...blocks];
    if (index >= 0 && !next[index].gap) next[index] = { ...next[index], gap: "\n\n" };
    next.splice(index + 1, 0, { kind: "text", raw, gap: index + 1 < blocks.length ? "\n\n" : "\n" });
    emit(next);
  };
  return (
    <div className="doc-page" data-testid="document-page">
      {!blocks.length && <p className="text-sm text-slate-500">This document is empty.</p>}
      {blocks.map((block, i) => (
        <div key={i} className="group/block">
          {block.kind === "table"
            ? <TableBlock raw={block.raw} gherkin={gherkin} label={`Table ${blocks.slice(0, i).filter((b) => b.kind === "table").length + 1}`} readOnly={readOnly} onChange={(raw) => update(i, raw)} />
            : <TextBlock raw={block.raw} gherkin={gherkin} readOnly={readOnly} onChange={(raw) => (raw.trim() ? update(i, raw) : remove(i))} onRemove={() => remove(i)} />}
          {!readOnly && !gherkin && (
            <div className="hidden h-7 items-center gap-1.5 focus-within:flex group-hover/block:flex" aria-label="Insert after this block">
              <Plus className="h-3.5 w-3.5 text-slate-400" /><Insert documentId={documentId} onInsert={(raw) => insert(i, raw)} onError={onError} />
            </div>
          )}
        </div>
      ))}
      {!readOnly && !gherkin && <div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-slate-200 pt-3 dark:border-slate-800" data-testid="doc-toolbar"><Insert documentId={documentId} onInsert={(raw) => insert(blocks.length - 1, raw)} onError={onError} /></div>}
    </div>
  );
}
