import { Button, Card } from "../../components/ui";
import { Template } from "./types";

export function Catalog({ templates, stdioAllowed, onPick }: { templates: Template[]; stdioAllowed: boolean; onPick: (t: Template) => void }) {
  return (
    <Card title="Add from catalog">
      <p className="mb-2 text-xs text-slate-500">Templates only. Picking one fills the add form; nothing is registered until you save it.</p>
      {templates.length === 0 && <p className="text-sm text-slate-500">The catalog has no templates.</p>}
      <div className="grid gap-2 md:grid-cols-2">
        {templates.map((t) => (
          <div key={t.id} className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800" data-testid="mcp-template">
            <div className="min-w-0"><p className="text-sm font-semibold">{t.name} <span className="text-xs font-normal text-slate-500">{t.transport}</span></p><p className="text-xs text-slate-500">{t.description}</p></div>
            <Button variant="secondary" disabled={t.transport === "stdio" && !stdioAllowed} onClick={() => onPick(t)}>Use</Button>
          </div>
        ))}
      </div>
    </Card>
  );
}
