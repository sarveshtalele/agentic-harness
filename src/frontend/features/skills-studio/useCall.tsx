import { useCallback, useState } from "react";
import { ErrorNote, Spinner } from "../../components/ui";

type Failure = { message: string; replyFile?: string };

/** A rejected model reply comes back as detail {message, reply_file}; the message is shown, and the kept reply's file name. */
function failure(e: any): Failure {
  const detail = e?.detail;
  if (detail && typeof detail === "object" && typeof detail.message === "string") return { message: detail.message, replyFile: detail.reply_file };
  return { message: e?.message || "Request failed" };
}

export type Call = { busy: string; error: Failure | null; run: <T>(label: string, fn: () => Promise<T>) => Promise<T | undefined> };

/** One request at a time per step: `busy` holds the loading words while it runs. */
export function useCall(): Call {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<Failure | null>(null);
  const run = useCallback(async <T,>(label: string, fn: () => Promise<T>) => {
    setBusy(label); setError(null);
    try { return await fn(); } catch (e: any) { setError(failure(e)); return undefined; } finally { setBusy(""); }
  }, []);
  return { busy, error, run };
}

export function CallStatus({ call }: { call: Call }) {
  return (
    <div className="space-y-2">
      {call.busy && <div data-testid="studio-busy"><Spinner label={call.busy} /></div>}
      <ErrorNote message={call.error?.message} />
      {call.error?.replyFile && <p className="text-xs text-slate-500">The model&apos;s reply was kept for debugging: <span className="mono">{call.error.replyFile}</span></p>}
    </div>
  );
}
