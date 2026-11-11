import { Save } from "lucide-react";
import { Button, inputClass } from "../../components/ui";
import { reopenText } from "./lib";

type Props = { doc: any; user: any; note: string; setNote: (v: string) => void; busy: boolean; dirty: boolean; onSave: () => void; onDiscard: () => void };

export function SaveBar({ doc, user, note, setNote, busy, dirty, onSave, onDiscard }: Props) {
  return (
    <div className="sticky bottom-0 z-10 mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white/95 p-2 backdrop-blur dark:border-slate-800 dark:bg-[#0b1329]/95" data-testid="save-bar">
      <span className="text-xs text-slate-500" data-testid="signing-as">Signing as {user?.username}</span>
      <input aria-label="Change note" className={`${inputClass} max-w-md`} placeholder="What changed" value={note} onChange={(e) => setNote(e.target.value)} />
      {Array.isArray(doc.would_reopen) && doc.would_reopen.length > 0 && <span className="text-xs text-amber-600 dark:text-amber-400" data-testid="reopen-warning">Saving a change reopens {reopenText(doc.would_reopen)}. Each needs a new approval on the Governance page.</span>}
      <Button onClick={onSave} busy={busy} disabled={!dirty}><Save className="h-4 w-4" /> Save version</Button>
      {dirty ? <><Button variant="secondary" onClick={() => onDiscard()}>Discard changes</Button><span className="text-xs text-amber-500">Unsaved changes</span></> : <span className="text-xs text-slate-500">Select any text or table cell to edit it</span>}
    </div>
  );
}
