import { Play, Sparkles, Upload } from "lucide-react";
import { ModelPicker } from "../../components/ModelPicker";
import { Button, Card, ErrorNote, Field, inputClass } from "../../components/ui";

type Props = { project: any; presets: any[]; brief: string; setBrief: (v: string) => void; title: string; setTitle: (v: string) => void; template: any; templateId: string; setTemplateId: (v: string) => void; safeTemplates: any[]; error: string; model: string; setModel: (v: string) => void; busy: boolean; disabled: boolean; onStart: () => void; onTemplateFile: (file?: File) => void };

export function RequirementsForm({ project, presets, brief, setBrief, title, setTitle, template, templateId, setTemplateId, safeTemplates, error, model, setModel, busy, disabled, onStart, onTemplateFile }: Props) {
  return (
    <Card title="New Requirements Specification">
      <div className="space-y-3">
        <div>
          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-1 text-xs">
            <span className="font-semibold text-slate-700 dark:text-slate-300">Project Brief</span>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-semibold text-slate-400">Project Presets:</span>
              {presets.map((p) => (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => {
                    setBrief(p.brief);
                    setTitle(p.title);
                  }}
                  className="inline-flex items-center gap-1 rounded-lg border border-indigo-200/80 bg-indigo-50/70 px-2 py-0.5 text-[11px] font-medium text-indigo-700 hover:border-indigo-400 hover:bg-indigo-100 dark:border-indigo-800/60 dark:bg-indigo-950/50 dark:text-indigo-300 dark:hover:bg-indigo-900/60 transition shadow-2xs"
                >
                  <Sparkles className="h-3 w-3 text-indigo-500" />
                  {p.name}
                </button>
              ))}
            </div>
          </div>
          <textarea
            name="brief"
            rows={5}
            className={inputClass}
            placeholder="What should be built, for whom, and why. Agents use only what you provide; unknowns become Open Questions."
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
          />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Document title">
            <input
              name="doc-title"
              className={inputClass}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={template?.name || `e.g., ${project.name || "System"} Business Requirements Document`}
            />
          </Field>
          <Field label="Template format">
            <select
              aria-label="Template"
              className={inputClass}
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              {safeTemplates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}{t.builtin ? "" : " (yours)"}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {template && Array.isArray(template.headings) && template.headings.length > 0 && (
          <p className="text-xs text-slate-500">
            <span className="font-semibold">Sections:</span> {template.headings.join(" · ")}
          </p>
        )}

        <label className="flex w-fit cursor-pointer items-center gap-1.5 text-xs font-semibold text-indigo-500 hover:underline">
          <Upload className="h-3.5 w-3.5" /> Upload your own template (Markdown .md)
          <input
            type="file"
            name="template-file"
            accept=".md"
            className="hidden"
            onChange={(e) => onTemplateFile(e.target.files?.[0])}
          />
        </label>

        <ErrorNote message={error} />
        <ModelPicker value={model} onChange={setModel} compact />

        <Button onClick={onStart} busy={busy} disabled={disabled}>
          <Play className="h-4 w-4" /> Generate Requirements Document
        </Button>
      </div>
    </Card>
  );
}
