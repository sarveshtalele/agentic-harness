import { Plus } from "lucide-react";
import { Button, Card, ErrorNote, inputClass } from "../../components/ui";

type Props = { title: string; setTitle: (v: string) => void; template: string; setTemplate: (v: string) => void; templates: any[]; onCreate: () => void; error: string };

export function NewDocumentCard({ title, setTitle, template, setTemplate, templates, onCreate, error }: Props) {
  return (
    <Card title="Author New Specification from Template" className="mb-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <input
          aria-label="New document title"
          placeholder="e.g. Payments Reconciliation BRD"
          className={`${inputClass} max-w-sm`}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <select
          aria-label="Template for new document"
          className={`${inputClass} max-w-xs`}
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
        >
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <Button onClick={onCreate} disabled={!title.trim()}>
          <Plus className="h-4 w-4" /> Create Document
        </Button>
      </div>
      <ErrorNote message={error} />
    </Card>
  );
}
