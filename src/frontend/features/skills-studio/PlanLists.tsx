import { inputClass } from "../../components/ui";
import { move, replace, RowTools, Section, Text } from "./ListEditors";
import { Plan } from "./types";

type Props = { plan: Plan; onChange: (p: Plan) => void };
const row = "flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 p-2 dark:border-slate-800";

export function Tasks({ plan, onChange }: Props) {
  const set = (tasks: string[]) => onChange({ ...plan, tasks });
  return (
    <Section title="Tasks" addLabel="Add task" onAdd={() => set([...plan.tasks, ""])} empty="No tasks. Add at least one.">
      {plan.tasks.map((t, i) => (
        <div key={i} className={row} data-testid={`studio-task-${i}`}>
          <textarea aria-label={`Task ${i + 1}`} className={`${inputClass} flex-1 h-16`} value={t} onChange={(e) => set(plan.tasks.map((x, k) => (k === i ? e.target.value : x)))} />
          <RowTools i={i} n={plan.tasks.length} onMove={(by) => set(move(plan.tasks, i, by))} onRemove={() => set(plan.tasks.filter((_, k) => k !== i))} />
        </div>
      ))}
    </Section>
  );
}

export function Files({ plan, onChange }: Props) {
  const set = (files: Plan["files"]) => onChange({ ...plan, files });
  return (
    <Section title="Files" addLabel="Add file" onAdd={() => set([...plan.files, { path: "", purpose: "" }])} empty="No files. SKILL.md is required.">
      {plan.files.map((f, i) => (
        <div key={i} className={row} data-testid={`studio-file-row-${i}`}>
          <Text label="Path" value={f.path} onChange={(path) => set(replace(plan.files, i, { path }))} />
          <Text wide label="Purpose" value={f.purpose} onChange={(purpose) => set(replace(plan.files, i, { purpose }))} />
          <RowTools i={i} n={plan.files.length} onMove={(by) => set(move(plan.files, i, by))} onRemove={() => set(plan.files.filter((_, k) => k !== i))} />
        </div>
      ))}
    </Section>
  );
}

export function Subagents({ plan, onChange }: Props) {
  const set = (subagents: Plan["subagents"]) => onChange({ ...plan, subagents });
  return (
    <Section title="Sub-agents" addLabel="Add sub-agent" onAdd={() => set([...plan.subagents, { name: "", role: "", when: "" }])} empty="No sub-agents: one agent does all the work">
      {plan.subagents.map((s, i) => (
        <div key={i} className={row} data-testid={`studio-subagent-${i}`}>
          <Text label="Sub-agent name" value={s.name} onChange={(name) => set(replace(plan.subagents, i, { name }))} />
          <Text wide label="Role" value={s.role} onChange={(role) => set(replace(plan.subagents, i, { role }))} />
          <Text wide label="When" value={s.when} onChange={(when) => set(replace(plan.subagents, i, { when }))} />
          <RowTools i={i} n={plan.subagents.length} onMove={(by) => set(move(plan.subagents, i, by))} onRemove={() => set(plan.subagents.filter((_, k) => k !== i))} />
        </div>
      ))}
    </Section>
  );
}

export function Formats({ plan, onChange }: Props) {
  const set = (formats: Plan["formats"]) => onChange({ ...plan, formats });
  return (
    <Section title="Output formats" addLabel="Add format" onAdd={() => set([...plan.formats, { name: "", purpose: "", template_path: "" }])} empty="No output formats.">
      {plan.formats.map((f, i) => (
        <div key={i} className={row} data-testid={`studio-format-${i}`}>
          <Text label="Format name" value={f.name} onChange={(name) => set(replace(plan.formats, i, { name }))} />
          <Text wide label="Purpose" value={f.purpose} onChange={(purpose) => set(replace(plan.formats, i, { purpose }))} />
          <Text label="Template path" value={f.template_path} onChange={(template_path) => set(replace(plan.formats, i, { template_path }))} />
          <RowTools i={i} n={plan.formats.length} onMove={(by) => set(move(plan.formats, i, by))} onRemove={() => set(plan.formats.filter((_, k) => k !== i))} />
        </div>
      ))}
    </Section>
  );
}
