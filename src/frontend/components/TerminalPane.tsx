"use client";

import "@xterm/xterm/css/xterm.css";
import { useEffect, useRef, useState } from "react";
import { Plus, SquareTerminal, X } from "lucide-react";
import { api } from "../lib/api";
import { Card, ErrorNote } from "./ui";

type Bridge = {
  open: (threadId: string, cols: number, rows: number) => Promise<{ id?: number; cwd?: string; shell?: string; error?: string }>;
  write: (id: number, data: string) => void;
  resize: (id: number, cols: number, rows: number) => void;
  close: (id: number) => void;
  onData: (cb: (id: number, data: string) => void) => () => void;
  onExit: (cb: (id: number, code: number) => void) => () => void;
};

const bridge = (): Bridge | undefined => (typeof window !== "undefined" ? (window as any).aqeTerminal : undefined);

/** The desktop app's Terminal pane (plan 11.2): your own shells in the project's workspace, and the harness's background
 * tasks as read-only tabs. Absent in a browser: only the desktop app exposes `window.aqeTerminal`. */
export function TerminalPane({ threadId }: { threadId: string }) {
  const [shells, setShells] = useState<{ id: number; label: string }[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [active, setActive] = useState<string>("");
  const [error, setError] = useState("");
  const [present, setPresent] = useState(false);

  useEffect(() => setPresent(!!bridge()), []);
  useEffect(() => {
    if (!present) return;
    const load = () => api(`/chats/${threadId}/terminal`).then((r) => setTasks(r.tasks)).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 4000); // background tasks keep printing while the harness works
    return () => clearInterval(timer);
  }, [present, threadId]);
  useEffect(() => () => shells.forEach((s) => bridge()?.close(s.id)), []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!present) return null;
  const add = async () => {
    const made = await bridge()!.open(threadId, 100, 20);
    if (made.error || made.id === undefined) return setError(made.error || "The terminal did not start");
    setError("");
    setShells((s) => [...s, { id: made.id!, label: `${made.shell} ${s.length + 1}` }]);
    setActive(`pty-${made.id}`);
  };
  const shown = active || (shells[0] ? `pty-${shells[0].id}` : tasks[0] ? `task-${tasks[0].id}` : "");
  const task = tasks.find((t) => `task-${t.id}` === shown);

  return (
    <Card title={<span className="flex items-center gap-1.5"><SquareTerminal className="h-4 w-4" /> Terminal</span>}>
      <ErrorNote message={error} />
      <div role="tablist" className="mb-2 flex flex-wrap items-center gap-1 text-xs">
        {shells.map((s) => (
          <span key={s.id} className={`flex items-center gap-1 rounded px-2 py-1 ${shown === `pty-${s.id}` ? "bg-slate-200 dark:bg-slate-700" : ""}`}>
            <button role="tab" aria-selected={shown === `pty-${s.id}`} onClick={() => setActive(`pty-${s.id}`)}>{s.label}</button>
            <button aria-label={`Close ${s.label}`} onClick={() => { bridge()?.close(s.id); setShells((all) => all.filter((x) => x.id !== s.id)); setActive(""); }}><X className="h-3 w-3" /></button>
          </span>
        ))}
        {tasks.map((t) => (
          <button key={t.id} role="tab" aria-selected={shown === `task-${t.id}`} title={t.status} onClick={() => setActive(`task-${t.id}`)}
            className={`rounded px-2 py-1 ${shown === `task-${t.id}` ? "bg-slate-200 dark:bg-slate-700" : ""}`}>{t.description}</button>
        ))}
        <button aria-label="New terminal" onClick={add} className="flex items-center gap-1 rounded px-2 py-1 hover:bg-slate-100 dark:hover:bg-slate-800"><Plus className="h-3 w-3" /> New terminal</button>
      </div>
      {shells.map((s) => <Pty key={s.id} id={s.id} hidden={shown !== `pty-${s.id}`} />)}
      {task && <pre data-testid="terminal-task" className="max-h-80 overflow-auto whitespace-pre-wrap rounded bg-slate-950 p-2 text-xs text-slate-100">{task.status}{"\n"}{task.output || "(no output yet)"}</pre>}
      {!shells.length && !tasks.length && <p className="text-sm text-slate-500">No terminal open. Start one to run your own commands in the project folder; the harness&apos;s background tasks appear here too.</p>}
    </Card>
  );
}

function Pty({ id, hidden }: { id: number; hidden: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const fit = useRef<any>(null);

  useEffect(() => {
    let disposed = false;
    const cleanups: (() => void)[] = [];
    (async () => {
      const [{ Terminal }, { FitAddon }] = await Promise.all([import("@xterm/xterm"), import("@xterm/addon-fit")]);
      if (disposed || !box.current) return;
      const term = new Terminal({ fontSize: 13, cursorBlink: true, convertEol: false });
      fit.current = new FitAddon();
      term.loadAddon(fit.current);
      term.open(box.current);
      fit.current.fit();
      bridge()!.resize(id, term.cols, term.rows);
      const typed = term.onData((data) => bridge()!.write(id, data));
      const sized = term.onResize(({ cols, rows }) => bridge()!.resize(id, cols, rows));
      cleanups.push(bridge()!.onData((from, data) => { if (from === id) term.write(data); }),
        bridge()!.onExit((from, code) => { if (from === id) term.write(`\r\n[process ended with exit code ${code}]\r\n`); }),
        () => typed.dispose(), () => sized.dispose(), () => term.dispose());
    })();
    return () => { disposed = true; cleanups.forEach((c) => c()); };
  }, [id]);
  useEffect(() => { if (!hidden) fit.current?.fit(); }, [hidden]);

  return <div ref={box} data-testid="terminal-pty" className={hidden ? "hidden" : "h-80 w-full"} />;
}
