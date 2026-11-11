import { Stethoscope } from "lucide-react";
import { Button, Card, Field, inputClass } from "../../components/ui";

export function DiagnoseCard({ trace, setTrace, onDiagnose }: { trace: string; setTrace: (v: string) => void; onDiagnose: () => void }) {
  return (
    <Card title="Diagnose Error Trace">
      <Field label="Paste stack trace or test log output">
        <textarea
          name="traceback"
          rows={5}
          className={`${inputClass} mono text-xs`}
          placeholder="e.g. AssertionError: expected 200 got 500 at..."
          value={trace}
          onChange={(e) => setTrace(e.target.value)}
        />
      </Field>
      <Button
        variant="secondary"
        className="mt-2.5 w-full justify-center"
        disabled={!trace.trim()}
        onClick={onDiagnose}
      >
        <Stethoscope className="h-4 w-4" /> Diagnose and Fix
      </Button>
    </Card>
  );
}
