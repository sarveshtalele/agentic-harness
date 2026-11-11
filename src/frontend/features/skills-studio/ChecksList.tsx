import { Badge } from "../../components/ui";
import { Check } from "./types";

export function ChecksList({ checks }: { checks: Check[] }) {
  return (
    <ul className="space-y-1">
      {checks.map((c) => (
        <li key={c.check} data-testid={`studio-check-${c.check}`} data-passed={String(c.passed)} className="flex items-start gap-2 text-xs">
          <Badge tone={c.passed ? "emerald" : "rose"}>{c.passed ? "passed" : "failed"}</Badge>
          <span><span className="font-semibold">{c.check}</span>{c.detail && <span className="text-slate-500">: {c.detail}</span>}</span>
        </li>
      ))}
    </ul>
  );
}
