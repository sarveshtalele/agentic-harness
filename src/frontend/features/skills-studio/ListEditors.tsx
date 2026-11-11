import { ReactNode } from "react";
import { Button, Empty, inputClass } from "../../components/ui";

export function move<T>(list: T[], i: number, by: number): T[] {
  const j = i + by;
  if (j < 0 || j >= list.length) return list;
  const next = [...list];
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}

export function replace<T>(list: T[], i: number, patch: Partial<T>): T[] {
  return list.map((x, k) => (k === i ? { ...x, ...patch } : x));
}

export function RowTools({ i, n, onMove, onRemove }: { i: number; n: number; onMove: (by: number) => void; onRemove: () => void }) {
  return (
    <div className="flex shrink-0 gap-1">
      <Button variant="secondary" aria-label="Move up" disabled={i === 0} onClick={() => onMove(-1)} className="!px-2 !py-1">↑</Button>
      <Button variant="secondary" aria-label="Move down" disabled={i === n - 1} onClick={() => onMove(1)} className="!px-2 !py-1">↓</Button>
      <Button variant="danger" aria-label="Remove" onClick={onRemove} className="!px-2 !py-1">✕</Button>
    </div>
  );
}

export function Section({ title, onAdd, addLabel, empty, children }: { title: string; onAdd: () => void; addLabel: string; empty?: string; children: ReactNode[] }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between"><h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">{title}</h3><Button variant="secondary" onClick={onAdd} className="!py-1 text-xs">{addLabel}</Button></div>
      {children.length === 0 && empty && <Empty title={empty} />}
      {children}
    </div>
  );
}

export function Text({ label, value, onChange, wide }: { label: string; value: string; onChange: (v: string) => void; wide?: boolean }) {
  return <input aria-label={label} placeholder={label} className={`${inputClass} ${wide ? "flex-1" : "w-40"}`} value={value} onChange={(e) => onChange(e.target.value)} />;
}
