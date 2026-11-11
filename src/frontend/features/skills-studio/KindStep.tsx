import { Card } from "../../components/ui";
import { Kind } from "./types";

const kinds: { id: Kind; title: string; text: string }[] = [
  { id: "instructions", title: "Instructions only (SKILL.md + references)", text: "For methods, checklists and formats." },
  { id: "scripts", title: "Script based (scripts + tests)", text: "For deterministic work such as parsing or converting. It runs tests in the desktop app only." },
];

export function KindStep({ kind, onKind }: { kind: Kind | ""; onKind: (k: Kind) => void }) {
  return (
    <Card title="2. Kind of skill">
      <div className="grid gap-3 sm:grid-cols-2">
        {kinds.map((k) => (
          <button key={k.id} type="button" data-testid={`studio-kind-${k.id}`} aria-pressed={kind === k.id} onClick={() => onKind(k.id)}
            className={`rounded-xl border p-4 text-left transition ${kind === k.id ? "border-indigo-500 bg-indigo-500/10" : "border-slate-300 hover:border-indigo-400 dark:border-slate-700"}`}>
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{k.title}</p>
            <p className="mt-1 text-xs text-slate-500">{k.text}</p>
          </button>
        ))}
      </div>
    </Card>
  );
}
