import { Button, inputClass } from "../../components/ui";
import { move, replace, RowTools, Section, Text } from "./ListEditors";
import { Assertion, Plan } from "./types";

const kinds: Assertion["kind"][] = ["contains", "not_contains", "regex"];

export function EvalCases({ plan, onChange }: { plan: Plan; onChange: (p: Plan) => void }) {
  const set = (eval_cases: Plan["eval_cases"]) => onChange({ ...plan, eval_cases });
  const cases = plan.eval_cases;
  return (
    <Section title="Eval cases" addLabel="Add eval case" onAdd={() => set([...cases, { input: "", assertions: [{ kind: "contains", value: "" }] }])} empty="No eval cases. The server needs 2 to 6.">
      {cases.map((c, i) => {
        const setAssertions = (assertions: Assertion[]) => set(replace(cases, i, { assertions }));
        return (
          <div key={i} className="space-y-2 rounded-lg border border-slate-200 p-2 dark:border-slate-800" data-testid={`studio-eval-${i}`}>
            <div className="flex gap-2">
              <textarea aria-label={`Eval input ${i + 1}`} className={`${inputClass} h-20 flex-1`} value={c.input} onChange={(e) => set(replace(cases, i, { input: e.target.value }))} />
              <RowTools i={i} n={cases.length} onMove={(by) => set(move(cases, i, by))} onRemove={() => set(cases.filter((_, k) => k !== i))} />
            </div>
            {c.assertions.map((a, j) => (
              <div key={j} className="flex flex-wrap items-center gap-2 pl-4">
                <select aria-label="Assertion kind" className={`${inputClass} !w-36`} value={a.kind} onChange={(e) => setAssertions(replace(c.assertions, j, { kind: e.target.value as Assertion["kind"] }))}>
                  {kinds.map((k) => <option key={k}>{k}</option>)}
                </select>
                <Text wide label="Assertion value" value={a.value} onChange={(value) => setAssertions(replace(c.assertions, j, { value }))} />
                <Button variant="danger" aria-label="Remove assertion" className="!px-2 !py-1" onClick={() => setAssertions(c.assertions.filter((_, k) => k !== j))}>✕</Button>
              </div>
            ))}
            <Button variant="secondary" className="ml-4 !py-1 text-xs" onClick={() => setAssertions([...c.assertions, { kind: "contains", value: "" }])}>Add assertion</Button>
          </div>
        );
      })}
    </Section>
  );
}
