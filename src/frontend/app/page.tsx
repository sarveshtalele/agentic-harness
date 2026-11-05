"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Archive,
  CheckSquare,
  FolderGit2,
  FolderKanban,
  Bug,
  Pencil,
  Plus,
  Search,
  Trash2,
  Undo2,
  Terminal,
  Layers,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  ChevronRight
} from "lucide-react";

// Platform UI Components
import { AppShell } from "../components/AppShell";
import { Badge, Button, Empty, ErrorNote, Field, inputClass, Spinner, useToast } from "../components/ui";
import { api, upload, when } from "../lib/api";

// Harness Components
import { LeftSidebar, SessionItem } from "../components/left-sidebar/LeftSidebar";
import { ChatContainer } from "../components/chat/ChatContainer";
import { ContextInspector } from "../components/inspector/ContextInspector";
import { MCPSettingsModal } from "../components/modals/MCPSettingsModal";
import { ModelConfigModal } from "../components/modals/ModelConfigModal";
import { SessionState, ChatMessage, ToolCall } from "../lib/maf/types";
import { getAgent } from "../lib/qe/agents";
import { AGUIProtocolHandler } from "../lib/maf/protocol/agui";

export default function UnifiedPlatformAndHarnessPage() {
  // Navigation View State: "harness" | "projects"
  const [activeView, setActiveView] = useState<"harness" | "projects">("harness");

  // ==========================================
  // 1. Projects Hub State
  // ==========================================
  const [projects, setProjects] = useState<any[] | null>(null);
  const [archived, setArchived] = useState(false);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [projectError, setProjectError] = useState("");
  const toast = useToast();

  const loadProjects = useCallback(() => {
    api(`/projects?archived=${archived}`)
      .then(setProjects)
      .catch((e) => setProjectError(`Cannot reach the backend: ${e.message}`));
  }, [archived]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const shownProjects = (projects || []).filter((p) =>
    `${p.name} ${p.description}`.toLowerCase().includes(query.toLowerCase())
  );

  const setArchivedFlag = async (p: any, value: boolean) => {
    await api(`/projects/${p.id}`, { method: "PATCH", json: { archived: value } });
    loadProjects();
  };

  const renameProject = async (p: any) => {
    const name = prompt("Project name", p.name)?.trim();
    if (!name || name === p.name) return;
    await api(`/projects/${p.id}`, { method: "PATCH", json: { name } });
    toast("Project renamed");
    loadProjects();
  };

  const removeProject = async (p: any) => {
    if (
      prompt(
        `This permanently deletes "${p.name}", its repository copy, documents, and audit ledger.\nType the project name to confirm.`
      ) !== p.name
    )
      return;
    await api(`/projects/${p.id}`, { method: "DELETE" });
    toast("Project deleted");
    loadProjects();
  };

  // Open project directly inside Harness
  const openProjectInHarness = (project: any) => {
    setActiveView("harness");
    setTimeout(() => {
      handleSendMessage(`/project ${project.id}`);
    }, 200);
  };

  // ==========================================
  // 2. Harness Command Center State
  // ==========================================
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [agentsList, setAgentsList] = useState<any[]>([]);
  const [pluginsList, setPluginsList] = useState<any[]>([]);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [skillsList, setSkillsList] = useState<any[]>([]);
  const [currentModel, setCurrentModel] = useState("gpt-4o");
  const [isModelConfigured, setIsModelConfigured] = useState<boolean>(false);

  // Layout states
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [mcpModalOpen, setMcpModalOpen] = useState(false);
  const [modelConfigModalOpen, setModelConfigModalOpen] = useState(false);

  // Streaming & Stop states
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingThought, setStreamingThought] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch LLM configuration
  const loadConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const data = await res.json();
        if (data.model) setCurrentModel(data.model);
        setIsModelConfigured(Boolean(data.configured));
      }
    } catch (e) {
      console.error("Failed to load config:", e);
    }
  }, []);

  // Fetch Metadata (Agents, Plugins, MCP, 58 Local Skills)
  const loadMetadata = useCallback(async () => {
    try {
      const [agRes, mcpRes, plugRes, skRes] = await Promise.all([
        fetch("/api/agents"),
        fetch("/api/mcp"),
        fetch("/api/plugins"),
        fetch("/api/skills"),
      ]);
      if (agRes.ok) {
        const agData = await agRes.json();
        if (agData.agents) setAgentsList(agData.agents);
      }
      if (mcpRes.ok) {
        const mcpData = await mcpRes.json();
        if (mcpData.servers) setMcpServers(mcpData.servers);
      }
      if (plugRes.ok) {
        const plugData = await plugRes.json();
        if (plugData.plugins) setPluginsList(plugData.plugins);
      }
      if (skRes.ok) {
        const skData = await skRes.json();
        if (skData.skills) setSkillsList(skData.skills);
      }
    } catch (e) {
      console.error("Failed to load metadata:", e);
    }
  }, []);

  // Fetch Sessions
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) return;
      const data = await res.json();
      if (data.sessions) {
        setSessions(data.sessions);
        if (!activeSessionId && data.sessions.length > 0) {
          selectSession(data.sessions[0].id);
        } else if (data.sessions.length === 0) {
          createNewSession("Agentic QE Campaign", "plan");
        }
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  }, [activeSessionId]);

  const selectSession = async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.session) {
        setActiveSessionId(id);
        setSessionState(data.session);
      }
    } catch (err) {
      console.error(`Failed to load session ${id}:`, err);
    }
  };

  const createNewSession = async (name?: string, mode: "plan" | "execute" = "plan") => {
    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || `QE Session #${sessions.length + 1}`, mode }),
      });
      const data = await res.json();
      if (data.session) {
        setActiveSessionId(data.session.id);
        setSessionState(data.session);
        loadSessions();
      }
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const deleteSession = async (id: string) => {
    try {
      await fetch(`/api/sessions/${id}`, { method: "DELETE" });
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id) {
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          createNewSession();
        }
      }
    } catch (err) {
      console.error(`Failed to delete session ${id}:`, err);
    }
  };

  useEffect(() => {
    loadConfig();
    loadMetadata();
    loadSessions();
  }, [loadConfig, loadMetadata, loadSessions]);

  // Mode switcher
  const handleToggleMode = async (newMode: "plan" | "execute") => {
    if (!sessionState || !activeSessionId) return;
    setSessionState((prev) => (prev ? { ...prev, mode: newMode } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode }),
      });
    } catch (e) {
      console.error("Failed to update mode:", e);
    }
  };

  // Agent selector
  const handleSelectAgent = async (agentId: string) => {
    if (!sessionState || !activeSessionId) return;
    setSessionState((prev) => (prev ? { ...prev, activeAgentId: agentId } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activeAgentId: agentId }),
      });
    } catch (e) {
      console.error("Failed to update agent:", e);
    }
  };

  // Todo checkmark toggle
  const handleToggleTodo = async (id: string, completed: boolean) => {
    if (!sessionState || !activeSessionId) return;
    const updated = sessionState.todos.map((t) =>
      t.id === id
        ? {
            ...t,
            status: (completed ? "completed" : "pending") as "completed" | "pending",
            completedAt: completed ? Date.now() : undefined,
          }
        : t
    );
    setSessionState((prev) => (prev ? { ...prev, todos: updated } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ todos: updated }),
      });
    } catch (e) {
      console.error("Failed to update todos:", e);
    }
  };

  // Manual todo add
  const handleAddTodo = async (title: string) => {
    if (!sessionState || !activeSessionId) return;
    const newTodo = {
      id: `todo-${Date.now()}`,
      title,
      status: "pending" as const,
      createdAt: Date.now(),
      agentId: sessionState.activeAgentId,
    };
    const updated = [...sessionState.todos, newTodo];
    setSessionState((prev) => (prev ? { ...prev, todos: updated } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ todos: updated }),
      });
    } catch (e) {
      console.error("Failed to add todo:", e);
    }
  };

  // Stop Execution Feature
  const handleStopExecution = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (activeSessionId) {
      try {
        await fetch("/api/stop", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sessionId: activeSessionId }),
        });
      } catch (e) {
        console.error("Failed to send stop signal to backend:", e);
      }
    }
    setIsStreaming(false);
  };

  // Clear messages
  const handleClearSession = async () => {
    if (!sessionState || !activeSessionId) return;
    setSessionState((prev) => (prev ? { ...prev, messages: [] } : null));
  };

  // Resolve Human-In-The-Loop Quality Gate / Tool Approval
  const handleResolveApproval = async (approvalId: string, action: string, feedback?: string) => {
    try {
      await fetch("/api/approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approvalId,
          action,
          feedback,
        }),
      });
      if (activeSessionId) {
        await selectSession(activeSessionId);
      }
    } catch (e) {
      console.error("Failed to resolve approval:", e);
    }
  };

  // Export session JSON
  const handleExportSession = () => {
    if (!sessionState) return;
    const blob = new Blob([JSON.stringify(sessionState, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sessionState.name.toLowerCase().replace(/\s+/g, "-")}-session.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Send Message via SSE
  const handleSendMessage = async (userMessage: string) => {
    if (!userMessage.trim() || isStreaming || !activeSessionId) return;

    const optimisticUserMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: userMessage,
      createdAt: Date.now(),
    };

    setSessionState((prev) =>
      prev ? { ...prev, messages: [...prev.messages, optimisticUserMsg] } : null
    );

    setIsStreaming(true);
    setStreamingThought("");
    setStreamingContent("");

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    let currentThought = "";
    let currentContent = "";
    const activeToolCalls: ToolCall[] = [];

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: activeSessionId,
          message: userMessage,
          mode: sessionState?.mode || "plan",
          agentId: sessionState?.activeAgentId,
          systemPrompt: sessionState?.systemPrompt,
        }),
        signal: abortController.signal,
      });

      if (!response.body) {
        throw new Error("No response body stream received from backend.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const event = AGUIProtocolHandler.parseEvent(line);
          if (!event) continue;

          switch (event.type) {
            case "TEXT_CHUNK":
              currentContent += event.chunk;
              setStreamingContent(currentContent);
              break;

            case "THOUGHT_CHUNK":
              currentThought += event.chunk;
              setStreamingThought(currentThought);
              break;

            case "AGENT_SWITCH":
              setSessionState((prev) =>
                prev ? { ...prev, activeAgentId: event.agentId } : null
              );
              break;

            case "STATE_DELTA":
              setSessionState((prev) => (prev ? { ...prev, ...event.delta } : null));
              break;

            case "TOOL_CALL_START":
              activeToolCalls.push({
                id: event.toolCallId,
                name: event.toolName,
                args: event.args,
                status: "running",
                gateNumber: event.gate?.gateNumber,
              });
              break;

            case "TOOL_CALL_RESULT":
              const tc = activeToolCalls.find((t) => t.id === event.toolCallId);
              if (tc) {
                tc.result = event.result;
                tc.error = event.error;
                tc.status = event.error ? "failed" : "completed";
              }
              break;

            case "TOOL_APPROVAL_REQUEST":
              const pendingTc = activeToolCalls.find((t) => t.id === event.toolCallId);
              if (pendingTc) {
                pendingTc.status = "waiting_approval";
                pendingTc.approvalRequired = true;
              } else {
                activeToolCalls.push({
                  id: event.toolCallId,
                  name: event.toolName,
                  args: event.args,
                  status: "waiting_approval",
                  approvalRequired: true,
                  gateNumber: event.gate?.gateNumber,
                });
              }
              currentContent += `\n\n🛡️ **Quality Gate Action Required:** Tool \`${event.toolName}\` requires explicit verification.\n`;
              setStreamingContent(currentContent);
              break;

            case "ERROR":
              if (event.code === "MODEL_NOT_CONFIGURED") {
                setIsModelConfigured(false);
              }
              currentContent += `\n\n> ⚠️ **Error [${event.code || "SYSTEM_ERROR"}]:** ${event.message}\n`;
              setStreamingContent(currentContent);
              break;

            case "ABORTED":
              currentContent += `\n\n⚠️ **Execution stopped by user.**`;
              setStreamingContent(currentContent);
              break;

            case "RUN_FINISHED":
              break;
          }
        }
      }

      await selectSession(activeSessionId);
      loadSessions();
    } catch (err: any) {
      if (err.name === "AbortError") {
        setStreamingContent((prev) => `${prev}\n\n⚠️ **Execution stopped by user.**`);
      } else {
        console.error("Stream processing error:", err);
        setStreamingContent((prev) => `${prev}\n\n❌ **Error:** ${err.message}`);
      }
    } finally {
      setIsStreaming(false);
      setStreamingThought("");
      setStreamingContent("");
      abortControllerRef.current = null;
    }
  };

  const activeAgent = getAgent(
    sessionState?.activeAgentId || "principal-test-architect"
  );

  const all = projects || [];
  const needing = all.filter((p) => p.pending > 0).length;
  const stats: [string, number, any, string, string][] = [
    ["Projects", all.length, FolderKanban, "/", "projects"],
    ["Need my approval", needing, CheckSquare, "/approvals", "need-approval"],
    ["Open findings", all.reduce((n, p) => n + p.findings, 0), Bug, "/findings", "findings"],
    ["Documents", all.reduce((n, p) => n + p.documents, 0), FolderGit2, "/documents", "documents"],
  ];

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-[var(--bg-primary)]">
      {/* Top Universal App Bar: Switch between Harness Command Center & Platform Projects Hub */}
      <header className="flex h-11 shrink-0 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-4 select-none z-30">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-600 font-mono text-xs font-bold text-white shadow-sm">
              QE
            </span>
            <span className="text-xs font-bold tracking-tight text-[var(--text-primary)]">
              Agentic QE Platform
            </span>
          </div>

          <div className="h-4 w-[1px] bg-[var(--border-subtle)]" />

          {/* View Mode Switcher Pills */}
          <div className="flex items-center gap-1 rounded-lg bg-[var(--bg-tertiary)] p-0.5 border border-[var(--border-subtle)]">
            <button
              onClick={() => setActiveView("harness")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                activeView === "harness"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              <Terminal className="h-3.5 w-3.5" />
              <span>⚡ QE Harness Command Center</span>
              <span className="rounded-full bg-indigo-500/30 px-1.5 py-0.2 text-[10px] font-mono">
                {skillsList.length || 58} Skills
              </span>
            </button>

            <button
              onClick={() => setActiveView("projects")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                activeView === "projects"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              <FolderKanban className="h-3.5 w-3.5" />
              <span>📂 Projects & Platform Hub</span>
              <span className="rounded-full bg-slate-500/20 px-1.5 py-0.2 text-[10px] font-mono">
                {all.length}
              </span>
            </button>
          </div>
        </div>

        {/* Global Navigation Shortcuts */}
        <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
          <Link
            href="/approvals"
            className="flex items-center gap-1 hover:text-indigo-400 transition"
          >
            <CheckSquare className="h-3.5 w-3.5 text-amber-500" />
            <span>Approvals ({needing})</span>
          </Link>

          <Link
            href="/findings"
            className="flex items-center gap-1 hover:text-indigo-400 transition"
          >
            <Bug className="h-3.5 w-3.5 text-rose-500" />
            <span>Findings ({all.reduce((n, p) => n + p.findings, 0)})</span>
          </Link>

          <Link
            href="/documents"
            className="flex items-center gap-1 hover:text-indigo-400 transition"
          >
            <FolderGit2 className="h-3.5 w-3.5 text-blue-500" />
            <span>Documents ({all.reduce((n, p) => n + p.documents, 0)})</span>
          </Link>

          <div className="h-3.5 w-[1px] bg-[var(--border-subtle)]" />

          {/* Quick Project Binder in Harness */}
          {activeView === "harness" && all.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-[var(--text-muted)]">Target Project:</span>
              <select
                className="bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] rounded px-2 py-0.5 text-xs text-[var(--text-primary)] outline-none"
                onChange={(e) => {
                  if (e.target.value) {
                    handleSendMessage(`/project ${e.target.value}`);
                  }
                }}
                defaultValue=""
              >
                <option value="" disabled>
                  Select Project Context...
                </option>
                {all.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.id})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </header>

      {/* Main View Area */}
      {activeView === "harness" ? (
        <div className="flex flex-1 overflow-hidden">
          {/* Claude Code Desktop Left Sidebar */}
          <LeftSidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={selectSession}
            onNewSession={() => createNewSession()}
            onDeleteSession={deleteSession}
            onOpenModelConfig={() => setModelConfigModalOpen(true)}
            onOpenMCPSettings={() => setMcpModalOpen(true)}
            sessionState={sessionState}
            agentsList={agentsList}
            toolsUsed={sessionState?.toolsUsed || {}}
            pluginsList={pluginsList}
            mcpServers={mcpServers}
            isOpen={sidebarOpen}
            onToggleOpen={() => setSidebarOpen(!sidebarOpen)}
            currentModel={currentModel}
            isModelConfigured={isModelConfigured}
            skillsList={skillsList}
            onSelectSkill={(cmd) => handleSendMessage(cmd)}
          />

          {/* Center Chat Canvas */}
          <ChatContainer
            sessionName={sessionState?.name || "Agentic QE Campaign"}
            workingDir={sessionState?.workingDir || "workspace"}
            mode={sessionState?.mode || "plan"}
            onToggleMode={handleToggleMode}
            activeAgent={activeAgent}
            onSelectAgent={handleSelectAgent}
            agents={agentsList}
            messages={sessionState?.messages || []}
            streamingThought={streamingThought}
            streamingContent={streamingContent}
            isStreaming={isStreaming}
            onSendMessage={handleSendMessage}
            onStopExecution={handleStopExecution}
            onExportSession={handleExportSession}
            onClearSession={handleClearSession}
            onToggleInspector={() => setInspectorOpen(!inspectorOpen)}
            isInspectorOpen={inspectorOpen}
            currentModel={currentModel}
            isModelConfigured={isModelConfigured}
            onOpenModelConfig={() => setModelConfigModalOpen(true)}
            skills={skillsList}
            onResolveApproval={handleResolveApproval}
          />

          {/* Right Context Inspector */}
          {sessionState && (
            <ContextInspector
              todos={sessionState.todos}
              ledger={sessionState.ledger}
              gates={sessionState.gates}
              onToggleTodo={handleToggleTodo}
              onAddTodo={handleAddTodo}
              isOpen={inspectorOpen}
              onToggleOpen={() => setInspectorOpen(!inspectorOpen)}
            />
          )}

          {/* Modals */}
          <ModelConfigModal
            isOpen={modelConfigModalOpen}
            onClose={() => setModelConfigModalOpen(false)}
            onConfigSaved={() => loadConfig()}
          />

          <MCPSettingsModal
            isOpen={mcpModalOpen}
            onClose={() => setMcpModalOpen(false)}
          />
        </div>
      ) : (
        /* Projects & Platform Hub View */
        <div className="flex-1 overflow-y-auto">
          <AppShell>
            {!archived && projects !== null && all.length > 0 && (
              <dl className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                {stats.map(([label, value, Icon, href, id]) => (
                  <Link
                    key={label}
                    href={href}
                    data-testid={`stat-${id}`}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 hover:border-indigo-500/60 dark:border-slate-800 dark:bg-[#0b1329]"
                  >
                    <Icon
                      className={`h-5 w-5 ${
                        id === "need-approval" && value > 0 ? "text-amber-500" : "text-indigo-500"
                      }`}
                    />
                    <span>
                      <dd className="text-xl font-bold leading-tight">{value}</dd>
                      <dt className="text-xs text-slate-500">{label}</dt>
                    </span>
                  </Link>
                ))}
              </dl>
            )}

            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h1 className="text-xl font-bold">
                {archived ? "Archived projects" : "Projects"}
              </h1>
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    aria-label="Search projects"
                    className={`${inputClass} w-56 pl-8`}
                    placeholder="Search projects"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </div>
                <Button variant="secondary" onClick={() => setArchived(!archived)}>
                  {archived ? "Show active" : "Show archived"}
                </Button>
                <Button onClick={() => setCreating(true)}>
                  <Plus className="h-4 w-4" /> New project
                </Button>
              </div>
            </div>

            <ErrorNote message={projectError} />
            {projects === null && !projectError && <Spinner />}
            {projects !== null && !shownProjects.length && (
              <Empty
                title={
                  query
                    ? "No project matches"
                    : archived
                    ? "No archived projects"
                    : "No projects yet"
                }
              >
                {!query &&
                  !archived &&
                  "Create a project, then connect a repository or start writing requirements."}
              </Empty>
            )}

            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {shownProjects.map((p) => (
                <article
                  key={p.id}
                  className="group flex flex-col rounded-xl border border-slate-200 bg-white p-4 transition hover:border-indigo-500/60 dark:border-slate-800 dark:bg-[#0b1329]"
                  data-testid="project-card"
                >
                  <div className="flex items-start justify-between">
                    <Link href={`/projects/${p.id}`} className="flex-1">
                      <h2 className="truncate font-bold hover:text-indigo-600 transition">
                        {p.name}
                      </h2>
                    </Link>
                    <button
                      onClick={() => openProjectInHarness(p)}
                      title="Open in MAF Harness"
                      className="flex items-center gap-1 rounded bg-indigo-600/10 hover:bg-indigo-600 hover:text-white px-2 py-0.5 text-[11px] font-semibold text-indigo-500 transition"
                    >
                      <Terminal className="h-3 w-3" />
                      <span>Harness</span>
                    </button>
                  </div>

                  <p className="mt-1 line-clamp-2 min-h-8 text-xs text-slate-600 dark:text-slate-400">
                    {p.description || "No description"}
                  </p>

                  <p className="mt-3 flex items-center gap-1.5 truncate text-xs text-slate-600 dark:text-slate-400">
                    <FolderGit2 className="h-3.5 w-3.5 shrink-0" />{" "}
                    {p.repo ? p.repo.url : "No repository"}
                  </p>

                  {p.repo?.languages?.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {p.repo.languages.map((l: string) => (
                        <Badge key={l} tone="indigo">
                          {l}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <dl className="mt-3 grid grid-cols-4 gap-1 text-center text-xs">
                    {[
                      ["Gates", `${p.gates_approved}/6`, "governance"],
                      ["Docs", p.documents, "documents"],
                      ["Runs", p.runs, "runs"],
                      ["Bugs", p.findings, "bugs"],
                    ].map(([label, value, tab]) => (
                      <Link
                        key={label as string}
                        href={`/projects/${p.id}/${tab}`}
                        data-testid={`card-${tab}`}
                        className="rounded-lg bg-slate-100 py-1 hover:ring-1 hover:ring-indigo-500 dark:bg-slate-900"
                      >
                        <dd className="font-bold">{value}</dd>
                        <dt className="text-[10px] text-slate-500">{label}</dt>
                      </Link>
                    ))}
                  </dl>

                  <footer className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                    <span>
                      {p.pending > 0 ? (
                        <Link href="/approvals">
                          <Badge tone="amber">{`${p.pending} awaiting approval`}</Badge>
                        </Link>
                      ) : (
                        `Updated ${when(p.updated_at)}`
                      )}
                    </span>
                    <span className="flex gap-1.5">
                      <button
                        aria-label={`Rename ${p.name}`}
                        title="Rename"
                        onClick={() => renameProject(p)}
                        className="hover:text-indigo-500"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        aria-label={archived ? `Restore ${p.name}` : `Archive ${p.name}`}
                        title={archived ? "Restore" : "Archive"}
                        onClick={() => setArchivedFlag(p, !archived)}
                        className="hover:text-indigo-500"
                      >
                        {archived ? <Undo2 className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                      </button>
                      <button
                        aria-label={`Delete ${p.name}`}
                        title="Delete"
                        onClick={() => removeProject(p)}
                        className="hover:text-rose-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </span>
                  </footer>
                </article>
              ))}
            </div>

            {creating && <NewProjectModal onClose={() => setCreating(false)} onCreated={loadProjects} />}
          </AppShell>
        </div>
      )}
    </div>
  );
}

function NewProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const project = await api("/projects", { json: { name, description } });
      try {
        if (url.trim()) await api(`/projects/${project.id}/repo/git`, { json: { url: url.trim() } });
        else if (file) {
          const form = new FormData();
          form.append("file", file);
          await upload(`/projects/${project.id}/repo/zip`, form);
        }
      } catch (err: any) {
        router.push(`/projects/${project.id}/repository?error=${encodeURIComponent(err.message)}`);
        return;
      }
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="New project"
    >
      <form
        onSubmit={submit}
        className="w-full max-w-lg space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-[#0b1329]"
      >
        <h2 className="text-lg font-bold">New project</h2>
        <Field label="Name">
          <input
            required
            autoFocus
            maxLength={120}
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="Description">
          <textarea
            className={inputClass}
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <Field
          label="Git URL (optional)"
          hint="Public HTTPS URL or owner/repo. For private repositories, add a connection in Settings, then use the Repository page."
        >
          <input
            className={inputClass}
            placeholder="https://github.com/owner/repo"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={!!file}
          />
        </Field>
        <Field label="Or upload a ZIP (optional)">
          <input
            type="file"
            accept=".zip"
            className={inputClass}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={!!url}
          />
        </Field>
        <ErrorNote message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner /> : "Create project"}
          </Button>
        </div>
      </form>
    </div>
  );
}
