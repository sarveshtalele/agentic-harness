"use client";

import { CopilotKit } from "@copilotkit/react-core/v2";
import { Brain, ExternalLink, MessageSquarePlus, Pencil, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, when } from "../../lib/api";
import { Button, ConfirmModal, Empty, ErrorNote, inputClass, Spinner, useToast } from "../../components/ui";
import { Conversation } from "./Conversation";

export function Chat({ projectId, standalone = false, defaultAgent = "project-copilot", onThread }: { projectId: string; standalone?: boolean; defaultAgent?: string; onThread?: (thread: any) => void }) {
  const [agents, setAgents] = useState<any[]>([]);
  const [threads, setThreads] = useState<any[]>([]);
  const [thread, setThread] = useState<any>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [memory, setMemory] = useState("");
  const [showMemory, setShowMemory] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();

  const loadThreads = useCallback(() => api(`/projects/${projectId}/chats`).then(setThreads), [projectId]);
  const loadMemories = useCallback(() => api(`/projects/${projectId}/memories`).then(setMemories), [projectId]);

  useEffect(() => {
    api("/chat/agents").then(setAgents);
    loadThreads().catch((e) => setError(e.message));
    loadMemories();
  }, [loadThreads, loadMemories]);

  useEffect(() => onThread?.(thread), [thread, onThread]);

  // title and message count arrive after the assistant replies
  useEffect(() => {
    if (!thread) return;
    const timer = setInterval(loadThreads, 5000);
    return () => clearInterval(timer);
  }, [thread, loadThreads]);

  const [chatToDelete, setChatToDelete] = useState<string | null>(null);

  const open = async (id: string) => setThread(await api(`/chats/${id}`));
  const create = async (agent = "project-copilot") => {
    setThread(null);  // the old chat closes at once, so nothing typed can land in it
    const created = await api(`/projects/${projectId}/chats`, { json: { agent } });
    await loadThreads();
    setThread({ ...created, messages: [] });
  };
  const remove = (id: string) => {
    setChatToDelete(id);
  };
  const confirmRemove = async () => {
    if (!chatToDelete) return;
    const id = chatToDelete;
    await api(`/chats/${id}`, { method: "DELETE" });
    if (thread?.id === id) setThread(null);
    loadThreads();
    setChatToDelete(null);
  };
  const rename = async (t: any) => {
    const title = prompt("Chat title", t.title);
    if (title) {
      await api(`/chats/${t.id}`, { method: "PATCH", json: { title } });
      loadThreads();
    }
  };
  const addMemory = async () => {
    if (!memory.trim()) return;
    await api(`/projects/${projectId}/memories`, { json: { content: memory } });
    setMemory("");
    loadMemories();
    toast("Saved to project memory");
  };

  return (
    <div className={`grid gap-3 md:grid-cols-[250px_1fr] ${standalone ? "h-screen p-3" : "h-[calc(100vh-110px)]"}`}>
      <div className="flex min-h-0 flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-[#0b1329]">
        <select key={agents.length} aria-label="Agent for new chat" className={inputClass} defaultValue={defaultAgent} id="new-agent">
          {agents.map((a) => <option key={a.key} value={a.key}>{a.name}</option>)}
        </select>
        <Button onClick={() => create((document.getElementById("new-agent") as HTMLSelectElement).value)}><MessageSquarePlus className="h-4 w-4" /> New chat</Button>
        <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto" aria-label="Saved chats">
          {threads.map((t) => (
            <li key={t.id} className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 ${thread?.id === t.id ? "bg-indigo-600/15" : "hover:bg-slate-100 dark:hover:bg-slate-900"}`}>
              <button className="min-w-0 flex-1 text-left" onClick={() => open(t.id)}>
                <span className="block truncate text-[13px] font-semibold">{t.title}</span>
                <span className="block truncate text-[11px] text-slate-500">{agents.find((a) => a.key === t.agent)?.name} · {when(t.updated_at)}</span>
              </button>
              <button aria-label={`Rename ${t.title}`} onClick={() => rename(t)} className="text-slate-400 opacity-0 hover:text-indigo-500 group-hover:opacity-100"><Pencil className="h-3.5 w-3.5" /></button>
              <button aria-label={`Delete ${t.title}`} onClick={() => remove(t.id)} className="text-slate-400 opacity-0 hover:text-rose-500 group-hover:opacity-100"><Trash2 className="h-3.5 w-3.5" /></button>
            </li>
          ))}
        </ul>
        <button onClick={() => setShowMemory(!showMemory)} className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-400"><Brain className="h-3.5 w-3.5" /> Project memory ({memories.length})</button>
        {showMemory && (
          <div className="max-h-52 space-y-1 overflow-y-auto">
            {memories.map((m) => (
              <div key={m.id} className="flex items-start gap-1 text-[11px]">
                <span className="flex-1">{m.content}</span>
                <button aria-label="Forget" onClick={() => api(`/memories/${m.id}`, { method: "DELETE" }).then(loadMemories)} className="text-slate-400 hover:text-rose-500"><Trash2 className="h-3 w-3" /></button>
              </div>
            ))}
            <div className="flex gap-1">
              <input className={inputClass} value={memory} onChange={(e) => setMemory(e.target.value)} placeholder="Add a fact to remember" />
              <Button variant="secondary" onClick={addMemory}>Add</Button>
            </div>
          </div>
        )}
        {!standalone && (
          <a href={`/chat/${projectId}`} target="atlas-chat" rel="noopener" onClick={(e) => { e.preventDefault(); window.open(`/chat/${projectId}`, `atlas-chat-${projectId}`, "width=1000,height=800"); }} className="flex items-center gap-1.5 text-xs font-semibold text-indigo-500"><ExternalLink className="h-3.5 w-3.5" /> Open in new window</a>
        )}
      </div>
      <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-[#0b1329]" data-testid="chat-pane">
        <ErrorNote message={error} />
        {thread ? (
          <CopilotKit key={thread.id} runtimeUrl="/api/copilotkit" enableInspector={false}>
            <Conversation thread={thread} onReplied={() => { loadThreads(); loadMemories(); }} />
          </CopilotKit>
        ) : threads.length || agents.length ? (
          <div className="m-auto max-w-md p-6"><Empty title="Start or open a chat">Each agent reads this project&apos;s real documents and code. Chats and memory are saved.</Empty></div>
        ) : <Spinner />}
      </div>

      <ConfirmModal
        open={!!chatToDelete}
        title="Delete Chat Conversation"
        message="Are you sure you want to delete this conversation thread? This action cannot be undone."
        confirmLabel="Delete Chat"
        variant="danger"
        onConfirm={confirmRemove}
        onCancel={() => setChatToDelete(null)}
      />
    </div>
  );
}
