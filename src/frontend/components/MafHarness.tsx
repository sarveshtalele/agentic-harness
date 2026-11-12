"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Circle, ListTodo } from "lucide-react";
import { api } from "../lib/api";
import { Chat } from "../features/chat/Chat";
import { Card, Empty, ErrorNote, Spinner, inputClass } from "./ui";
import { TerminalPane } from "./TerminalPane";

/** The project harness on MAF's create_harness_agent: the MAF chat with the harness agent, beside the thread's own todo list. */
export function MafHarness({ projectId, onProjectChange }: { projectId: string; onProjectChange: (id: string) => void }) {
  const [projects, setProjects] = useState<any[] | null>(null);
  const [thread, setThread] = useState<any>(null);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<string | null>(null);

  useEffect(() => {
    api("/projects").then(setProjects).catch((e) => setError(e.message));
    api("/profile").then((r) => setProfile(r.profile)).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!projects || !profile) return <Spinner label="Loading projects" />;
  const project = projects.find((p) => p.id === projectId);

  return (
    <div className="space-y-3 p-1">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold">Project harness</h1>
        <select aria-label="Harness project" className={`${inputClass} max-w-xs`} value={projectId} onChange={(e) => onProjectChange(e.target.value)}>
          <option value="">Choose a project</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <span className="text-xs text-slate-500">Microsoft Agent Framework harness: plans with todos, loads skills on demand, writes files and runs allowlisted commands in the project workspace, each after your approval{profile === "web" ? " (shared server: 5 sandbox slots)" : ""}.</span>
      </div>
      {!project ? (
        <Empty title={projects.length ? "Choose a project to start" : "No projects yet"}>
          {projects.length ? "The harness works on one project at a time." : <Link href="/projects" className="underline">Create a project first.</Link>}
        </Empty>
      ) : (
        <div className="grid gap-3 lg:grid-cols-[1fr_280px]">
          <Chat key={project.id} projectId={project.id} defaultAgent="harness" onThread={setThread} />
          <TodoPanel thread={thread} />
        </div>
      )}
      {project && thread?.agent === "harness" && <TerminalPane key={thread.id} threadId={thread.id} />}
    </div>
  );
}

function TodoPanel({ thread }: { thread: any }) {
  const [todos, setTodos] = useState<any[] | null>(null);
  const [error, setError] = useState("");
  const isHarness = thread?.agent === "harness";

  const load = useCallback(() => {
    if (!isHarness) return;
    api(`/chats/${thread.id}/todos`).then((r) => { setTodos(r.todos); setError(""); }).catch((e) => setError(e.message));
  }, [isHarness, thread?.id]);

  useEffect(() => {
    setTodos(null);
    load();
    if (!isHarness) return;
    const timer = setInterval(load, 4000);  // todos change while the harness works through a turn
    return () => clearInterval(timer);
  }, [load, isHarness]);

  return (
    <Card title={<span className="flex items-center gap-1.5"><ListTodo className="h-4 w-4" /> Todos</span>}>
      <div data-testid="harness-todos" className="space-y-1.5 text-sm">
        <ErrorNote message={error} />
        {!thread ? <p className="text-slate-500">Open or start a chat.</p>
          : !isHarness ? <p className="text-slate-500">Only the Project harness agent keeps a todo list.</p>
          : todos === null ? <Spinner label="Loading todos" />
          : !todos.length ? <p className="text-slate-500">No todos yet. Ask the harness to plan a task.</p>
          : todos.map((t) => (
            <div key={t.id} className="flex items-start gap-2" data-testid="harness-todo" data-done={t.done}>
              {t.done ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />}
              <span className={t.done ? "text-slate-500 line-through" : ""}>{t.title}</span>
            </div>
          ))}
      </div>
    </Card>
  );
}
