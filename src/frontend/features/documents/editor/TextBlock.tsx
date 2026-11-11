"use client";

import { Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Markdown } from "../../../components/ui";

export function GherkinText({ text }: { text: string }) {
  const keyword = /^(\s*)(Feature:|Rule:|Background:|Scenario Outline:|Scenario Template:|Scenario:|Example:|Examples:|Given|When|Then|And|But)(.*)$/;
  return (
    <pre className="mono overflow-auto text-sm leading-relaxed">
      {text.split("\n").map((line, i) => {
        const match = line.match(keyword);
        if (line.trim().startsWith("@")) return <div key={i} className="text-amber-600 dark:text-amber-400">{line}</div>;
        if (!match) return <div key={i}>{line || " "}</div>;
        const heading = match[2].endsWith(":");
        return <div key={i} className={heading ? "font-bold" : ""}>{match[1]}<span className="font-bold text-indigo-500">{match[2]}</span>{match[3]}</div>;
      })}
    </pre>
  );
}

export function TextBlock({ raw, gherkin, readOnly, onChange, onRemove }: { raw: string; gherkin: boolean; readOnly: boolean; onChange: (raw: string) => void; onRemove: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(raw);
  const box = useRef<HTMLTextAreaElement>(null);
  useEffect(() => setValue(raw), [raw]);
  useEffect(() => {
    if (editing) box.current?.focus();
  }, [editing]);
  const view = gherkin ? <GherkinText text={value} /> : <Markdown>{value}</Markdown>;
  if (readOnly) return view;
  if (editing) {
    return (
      <div className="rounded-lg border border-indigo-500 p-2" data-testid="text-editor">
        <textarea ref={box} aria-label="Edit this block" spellCheck={!gherkin} className="doc-text-input mono w-full bg-transparent text-[13px] leading-relaxed outline-none" value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={() => { setEditing(false); if (value !== raw) onChange(value); }}
          onKeyDown={(e) => { if (e.key === "Escape") { setValue(raw); setEditing(false); } }} />
        <div className="mt-2 border-t border-dashed border-slate-300 pt-2 dark:border-slate-700" data-testid="live-preview">{view}</div>
      </div>
    );
  }
  return (
    <div className="group/text relative">
      <div role="button" tabIndex={0} title="Select to edit" data-testid="text-block" className="cursor-text rounded-lg px-1 outline-none hover:bg-indigo-500/5 focus:ring-2 focus:ring-indigo-500"
        onClick={(e) => { if (!(e.target as HTMLElement).closest("a")) setEditing(true); }}
        onKeyDown={(e) => { if (e.key === "Enter" && e.target === e.currentTarget) { e.preventDefault(); setEditing(true); } }}>{view}</div>
      <button type="button" aria-label="Remove this block" title="Remove this block" className="absolute -right-5 top-1 text-slate-400 opacity-0 hover:text-rose-500 focus:opacity-100 group-hover/text:opacity-100" onClick={onRemove}><Trash2 className="h-3.5 w-3.5" /></button>
    </div>
  );
}
