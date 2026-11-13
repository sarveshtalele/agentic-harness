"use client";

import { useAgent, useCopilotKit } from "@copilotkit/react-core/v2";
import { Send, Square, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { ModelPicker } from "../../components/ModelPicker";
import { ApprovalCards, StatusLine, StatusTrail, useRunStatus } from "./RunStatus";
import { Button, ErrorNote, inputClass, Markdown } from "../../components/ui";


/** Headless CopilotKit over AG-UI: the UI waits until the agent is ready, so a send is never lost. */
export function Conversation({ thread, onReplied }: { thread: any; onReplied: () => void }) {
  const { agent, isReady } = useAgent({ agentId: thread.agent });
  const { copilotkit } = useCopilotKit();
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [model, setModel] = useState<string>(thread.model || "");
  const [tools, setTools] = useState<{ models: string[]; default: string; tools: Record<string, any> } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const run = useRunStatus(agent);
  const [trails, setTrails] = useState<Record<string, string[]>>({});  // the status lines each finished reply went through
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  useEffect(() => { api("/settings/models").then(setTools).catch(() => setTools(null)); }, [thread.id]);
  const current = model || tools?.default || "";
  const toolCheck = tools?.tools?.[current];
  useEffect(() => setModel(thread.model || ""), [thread.id, thread.model]);
  // the server checks the pick too: a model this account may not use is refused there
  const pickModel = async (next: string) => {
    setError("");
    try {
      await api(`/chats/${thread.id}`, { method: "PATCH", json: { model: next } });
      setModel(next);
    } catch (e: any) {
      setError(e.message);
    }
  };
  useEffect(() => {
    // eslint-disable-next-line react-hooks/immutability -- AG-UI reads the thread id from the agent object
    agent.threadId = thread.id;
    agent.setMessages(thread.messages.map((m: any) => ({ id: m.id, role: m.role, content: m.content })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent, thread.id]);
  const messages: any[] = agent.messages || [];
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages.length, running]);
  const runOnce = async (resume?: { interruptId: string; status: "resolved"; payload: { approved: boolean } }[]) => {
    setError("");
    setRunning(true);
    run.begin();
    try {
      await copilotkit.runAgent(resume ? { agent, resume } : { agent });
    } catch (e: any) {
      if (e?.name !== "AbortError") setError(e.message || "The agent could not reply");
    } finally {
      setRunning(false);
      const last = [...(agent.messages || [])].reverse().find((m: any) => m.role === "assistant");
      if (last) setTrails((t) => ({ ...t, [last.id]: [...(t[last.id] || []), ...run.takeTrail()] }));
      onReplied();
    }
  };
  const send = async () => {
    const content = text.trim();
    if (!content || running || !isReady) return;
    setText("");
    agent.addMessage({ id: crypto.randomUUID(), role: "user", content });
    await runOnce();
  };
  // every open interrupt needs an answer, so the run resumes once the last card is answered
  const answer = (id: string, approved: boolean) => {
    const next = { ...answers, [id]: approved };
    if (run.approvals.some((a) => !(a.id in next))) return setAnswers(next);
    setAnswers({});
    const resume = run.approvals.map((a) => ({ interruptId: a.id, status: "resolved" as const, payload: { approved: next[a.id] } }));
    run.clearApprovals();
    runOnce(resume);
  };
  const stop = () => copilotkit.stopAgent({ agent });  // aborts the request; the server stops the MAF run on disconnect
  const shown = messages.filter((m) => m.role === "user" || m.role === "assistant");
  return (
    <>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4" data-testid="chat-messages">
        {!shown.length && <p className="text-sm text-slate-500">{"Ask about this project\u2019s documents and code, or try /scan, /gates, /verify, /docs."}</p>}
        {shown.map((m) => (
          <div key={m.id} data-role={m.role} className={m.role === "user" ? "ml-auto w-fit max-w-[80%] rounded-xl bg-indigo-600 px-3 py-2 text-sm whitespace-pre-wrap text-white" : "max-w-full"}>
            {m.role === "user" ? (typeof m.content === "string" ? m.content : "") : (
              <>
                <StatusTrail lines={trails[m.id]} />
                {m.toolCalls?.length > 0 && <p data-testid="tool-calls" className="mono mb-1 flex flex-wrap items-center gap-1 text-[11px] text-slate-500"><Wrench className="h-3 w-3" /> {m.toolCalls.map((c: any) => c.function?.name).join(", ")}</p>}
                {m.content && <Markdown>{String(m.content)}</Markdown>}
              </>
            )}
          </div>
        ))}
        {running && <StatusLine text={run.status} />}
        {!running && <ApprovalCards approvals={run.approvals} busy={running} onAnswer={answer} />}
        <ErrorNote message={error} />
        <div ref={bottom} />
      </div>
      {toolCheck?.status === "failed" && <p role="alert" data-testid="tool-warning" className="mx-3 mb-1 rounded-lg bg-amber-500/15 px-3 py-1.5 text-xs text-amber-700 dark:text-amber-400">{current} failed the tool check ({toolCheck.reason}). It may ignore the project tools in this chat, so check its answers against the documents.</p>}
      <div className="flex items-center gap-2 border-t border-slate-200 px-3 pt-2 text-xs text-slate-500 dark:border-slate-800">Model <ModelPicker value={model} onChange={pickModel} compact /></div>
      <form className="flex items-end gap-2 px-3 pb-3 pt-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <textarea aria-label="Message" rows={2} disabled={!isReady} className={`${inputClass} resize-none`} placeholder={isReady ? "Ask about this project, its documents, or run an agent" : "Connecting"} value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
        {running ? <Button type="button" variant="secondary" onClick={stop} aria-label="Stop the agent" data-testid="stop-run"><Square className="h-4 w-4" /></Button>
          : <Button type="submit" disabled={!isReady || !text.trim()} aria-label="Send message"><Send className="h-4 w-4" /></Button>}
      </form>
    </>
  );
}
