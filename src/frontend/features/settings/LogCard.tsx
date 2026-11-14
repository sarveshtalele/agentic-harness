import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, Field, inputClass } from "../../components/ui";

export function LogCard() {
  const [logDay, setLogDay] = useState("");
  useEffect(() => {
    setLogDay(new Date().toLocaleDateString("en-CA")); // YYYY-MM-DD, set after mount so server and browser render alike
  }, []);
  return (
    <Card title="Application log">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Day"><input type="date" aria-label="Log day" className={inputClass} value={logDay} onChange={(e) => setLogDay(e.target.value)} /></Field>
        {logDay && <a className="inline-flex items-center gap-1.5 text-sm text-indigo-500 underline" href={`/api/logs?date=${logDay}`}><Download className="h-4 w-4" /> Download log for {logDay}</a>}
        {logDay && <a className="inline-flex items-center gap-1.5 text-sm text-indigo-500 underline" href={`/api/logs?date=${logDay}&kind=errors`}><Download className="h-4 w-4" /> Errors with stack traces</a>}
      </div>
      <p className="mt-2 text-xs text-slate-500">One log line per event that day. The errors file adds stack traces for warnings and errors. Passwords, keys, and request bodies are never written.</p>
    </Card>
  );
}
