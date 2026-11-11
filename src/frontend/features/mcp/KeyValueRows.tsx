import { Button, inputClass } from "../../components/ui";
import { Row } from "./types";

/** Name and value rows. Values are password inputs: they go to the server once and are never shown again. */
export function KeyValueRows({ label, rows, onChange, secret }: { label: string; rows: Row[]; onChange: (rows: Row[]) => void; secret?: boolean }) {
  const set = (i: number, patch: Partial<Row>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <div className="space-y-1">
      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{label}</span>
      {rows.map((r, i) => (
        <div key={i} className="flex gap-2">
          <input className={inputClass} placeholder="Name" aria-label={`${label} name ${i + 1}`} value={r.key} onChange={(e) => set(i, { key: e.target.value })} />
          <input className={inputClass} type={secret ? "password" : "text"} autoComplete="off" placeholder="Value" aria-label={`${label} value ${i + 1}`} value={r.value} onChange={(e) => set(i, { value: e.target.value })} />
          <Button type="button" variant="secondary" onClick={() => onChange(rows.filter((_, j) => j !== i))}>Remove</Button>
        </div>
      ))}
      <Button type="button" variant="secondary" onClick={() => onChange([...rows, { key: "", value: "" }])}>Add {label.toLowerCase()}</Button>
    </div>
  );
}
