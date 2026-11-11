"use client";

import { useEffect, useState, type KeyboardEvent } from "react";
import { api } from "../../lib/api";

export type SlashEntry = { name: string; kind: "command" | "skill"; plugin: string; description: string; argument_hint: string };

/** The "/" menu: typing "/" at the start of the message lists plugin commands and skills from /api/plugins/slash. */
export function useSlashMenu(text: string, setText: (next: string) => void, enabled: boolean) {
  const [entries, setEntries] = useState<SlashEntry[] | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState(0);
  const [dismissed, setDismissed] = useState("");
  useEffect(() => {
    if (enabled) api("/plugins/slash").then((got) => { setEntries(got); setError(""); }).catch((e) => setError(e.message || "Could not load commands"));
  }, [enabled]);
  const open = enabled && /^\/\S*$/.test(text) && dismissed !== text;
  const query = text.slice(1).toLowerCase();
  const items = open && entries
    ? entries.filter((e) => e.name.toLowerCase().includes(query))
        .sort((a, b) => Number(!a.name.toLowerCase().startsWith(query)) - Number(!b.name.toLowerCase().startsWith(query)) || a.name.localeCompare(b.name))
    : [];
  const current = Math.min(active, Math.max(items.length - 1, 0));
  const pick = (entry: SlashEntry) => { setText(`/${entry.name} `); setActive(0); };
  /** Returns true when the key was used by the menu, so the caller does not also send the message. */
  const onKeyDown = (e: KeyboardEvent): boolean => {
    if (!open) return false;
    if (e.key === "Escape") { setDismissed(text); return true; }
    if (!items.length) return false;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setActive((current + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length);
      return true;
    }
    if (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey)) { e.preventDefault(); pick(items[current]); return true; }
    return false;
  };
  return { open, items, active: current, pick, onKeyDown, loading: open && !entries && !error, error: open ? error : "" };
}

export function SlashMenu({ menu }: { menu: ReturnType<typeof useSlashMenu> }) {
  if (!menu.open) return null;
  const note = menu.error || (menu.loading ? "Loading commands and skills" : !menu.items.length ? "No command or skill matches" : "");
  return (
    <div data-testid="slash-menu" className="mx-3 mb-1 max-h-72 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
      {note ? <p className="px-3 py-2 text-xs text-slate-500">{note}</p> : (
        <ul role="listbox" aria-label="Commands and skills">
          {menu.items.map((entry, i) => (
            <li key={entry.name} role="option" aria-selected={i === menu.active} onMouseDown={(e) => { e.preventDefault(); menu.pick(entry); }}
              className={`cursor-pointer px-3 py-1.5 text-sm ${i === menu.active ? "bg-indigo-500/10" : ""}`}>
              <span className="mono text-slate-800 dark:text-slate-200">/{entry.name}</span>
              {entry.argument_hint && <span className="mono ml-2 text-xs text-slate-400">{entry.argument_hint}</span>}
              <span className="ml-2 rounded bg-slate-500/10 px-1.5 text-[10px] uppercase text-slate-500">{entry.kind}</span>
              {entry.description && <p className="truncate text-xs text-slate-500">{entry.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
