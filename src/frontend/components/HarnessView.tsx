"use client";

import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  FolderGit2,
  Layers,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Plus,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Square,
  Terminal,
  Wrench,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, Button, ErrorNote, Markdown, useToast } from "./ui";
import { api } from "../lib/api";

export interface SkillItem {
  name: string;
  displayName: string;
  description: string;
  category: string;
  command: string;
  assignedAgent?: string;
  version?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: number;
  thinking?: string;
  toolCalls?: Array<{
    id: string;
    name: string;
    args: Record<string, any>;
    result?: string;
    status: "running" | "completed" | "failed";
  }>;
  agentId?: string;
}

export interface HarnessSession {
  id: string;
  name: string;
  mode: "plan" | "execute";
  activeAgentId?: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  todos?: Array<{ id: string; text: string; completed: boolean; agentId?: string }>;
  ledger?: Array<{ type: string; title: string; detail: string; timestamp: number }>;
}

const AGENTS = [
  { id: "principal-test-architect", name: "Principal Test Architect", role: "Architect", icon: Compass, color: "text-indigo-500" },
  { id: "business-analyst", name: "Business Analyst", role: "BA", icon: Layers, color: "text-blue-500" },
  { id: "test-design-architect", name: "Test Design Architect", role: "Designer", icon: Cpu, color: "text-purple-500" },
  { id: "test-automation-engineer", name: "Test Automation Engineer", role: "Engineer", icon: Terminal, color: "text-cyan-500" },
  { id: "qa-execution-engineer", name: "QA Execution Engineer", role: "Executor", icon: Play, color: "text-emerald-500" },
  { id: "defect-diagnostician", name: "Defect Diagnostician", role: "Healer", icon: ShieldAlert, color: "text-amber-500" },
  { id: "coverage-auditor", name: "Coverage Auditor", role: "Auditor", icon: ShieldCheck, color: "text-violet-500" },
  { id: "confidence-reviewer", name: "Confidence Reviewer", role: "Reviewer", icon: CheckCircle2, color: "text-teal-500" },
  { id: "security-compliance-specialist", name: "Security Specialist", role: "Security", icon: Shield, color: "text-rose-500" },
];

const CORE_COMMANDS = [
  { cmd: "/plan", desc: "Formulate test strategy & risk allocation", icon: Compass },
  { cmd: "/execute", desc: "Run test execution workflows", icon: Play },
  { cmd: "/audit", desc: "Run full security & quality gates audit", icon: Shield },
  { cmd: "/heal", desc: "Diagnose and repair test failures", icon: Activity },
  { cmd: "/gates", desc: "Evaluate 8 QE quality gates", icon: ShieldCheck },
  { cmd: "/skills", desc: "Browse 59 discovered local machine skills", icon: Zap },
  { cmd: "/projects", desc: "List all target projects", icon: FolderGit2 },
];

export function HarnessView({
  initialProjectId,
  onProjectChange,
}: {
  initialProjectId?: string;
  onProjectChange?: (projectId: string) => void;
}) {
  const toast = useToast();

  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId || "");
  const [targetProject, setTargetProject] = useState<any>(null);
  const [gates, setGates] = useState<any[]>([]);

  const [sessions, setSessions] = useState<HarnessSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [currentSession, setCurrentSession] = useState<HarnessSession | null>(null);

  const [inputPrompt, setInputPrompt] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState("principal-test-architect");
  const [mode, setMode] = useState<"plan" | "execute">("plan");

  const [skillsCatalog, setSkillsCatalog] = useState<SkillItem[]>([]);
  const [activeTab, setActiveTab] = useState<"gates" | "todos" | "ledger" | "skills">("gates");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [error, setError] = useState("");

  const [llmConfig, setLlmConfig] = useState<any>(null);
  const [showSlashPalette, setShowSlashPalette] = useState(false);
  const [slashFilter, setSlashFilter] = useState("");
  const [paletteIndex, setPaletteIndex] = useState(0);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const msgSeqRef = useRef<number>(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 1. Sync target project with initialProjectId prop
  useEffect(() => {
    if (initialProjectId && initialProjectId !== selectedProjectId) {
      setSelectedProjectId(initialProjectId);
    }
  }, [initialProjectId]);

  // 2. Load Projects List & Centralized LLM Config
  useEffect(() => {
    api("/projects")
      .then((projs) => {
        setProjects(projs || []);
        if (!selectedProjectId && projs && projs.length > 0) {
          setSelectedProjectId(projs[0].id);
        }
      })
      .catch(() => {});

    api("/settings/llm")
      .then(setLlmConfig)
      .catch(() => setLlmConfig(null));
  }, [selectedProjectId]);

  // 2. Load Selected Target Project Details & Gates
  useEffect(() => {
    if (!selectedProjectId) return;
    Promise.all([
      api(`/projects/${selectedProjectId}`),
      api(`/projects/${selectedProjectId}/gates`),
    ])
      .then(([proj, gList]) => {
        setTargetProject(proj);
        setGates(gList || []);
      })
      .catch(() => {});
  }, [selectedProjectId]);

  // 3. Load Rich Skills Catalog from /api/harness/skills
  useEffect(() => {
    api("/harness/skills")
      .then((data) => {
        if (data && Array.isArray(data.skills)) {
          setSkillsCatalog(data.skills);
        }
      })
      .catch(() => {
        // Fallback to plugins endpoint if skills endpoint fails
        api("/harness/plugins")
          .then((pData) => {
            const plugins = pData.plugins || [];
            const qe = plugins.find((p: any) => p.id === "agentic-qe");
            if (qe && qe.skills) {
              const formatted: SkillItem[] = qe.skills.map((s: string) => ({
                name: s,
                displayName: s.replace("-", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                description: `Autonomous QE capability: ${s}`,
                category: "Quality Engineering",
                command: `/${s}`,
              }));
              setSkillsCatalog(formatted);
            }
          })
          .catch(() => {});
      });
  }, []);

  // 4. Load Sessions for Target Project
  const loadSessions = useCallback(async () => {
    try {
      const res = await api("/harness/sessions");
      const sessList = res.sessions || [];
      const projSessions = sessList.filter(
        (s: any) =>
          (selectedProjectId && s.id.startsWith(`proj_${selectedProjectId}_`)) ||
          (selectedProjectId && s.workingDir?.includes(selectedProjectId)) ||
          sessList.length <= 3
      );
      const listToUse = projSessions.length > 0 ? projSessions : sessList;

      if (listToUse.length === 0) {
        const created = await api("/harness/sessions", {
          method: "POST",
          json: {
            name: `${targetProject?.name || "Target Project"} QE Session`,
            mode: "plan",
            workingDir: targetProject?.repo?.url || "",
          },
        });
        setSessions([created.session]);
        setActiveSessionId(created.session.id);
        setCurrentSession(created.session);
      } else {
        setSessions(listToUse);
        if (!activeSessionId || !listToUse.find((s: any) => s.id === activeSessionId)) {
          setActiveSessionId(listToUse[0].id);
          setCurrentSession(listToUse[0]);
          setMode(listToUse[0].mode || "plan");
          if (listToUse[0].activeAgentId) setActiveAgentId(listToUse[0].activeAgentId);
        }
      }
    } catch (e: any) {
      console.warn("Could not load sessions:", e);
    }
  }, [selectedProjectId, targetProject, activeSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Keep messages scrolled
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages?.length, isExecuting]);

  // Handle Target Project Switching
  const handleSelectProject = (newProjectId: string) => {
    setSelectedProjectId(newProjectId);
    if (onProjectChange) {
      onProjectChange(newProjectId);
    }
  };

  // Create new session
  const handleCreateSession = async () => {
    try {
      const res = await api("/harness/sessions", {
        method: "POST",
        json: {
          name: `${targetProject?.name || "QE"} Session #${sessions.length + 1}`,
          mode: mode,
          workingDir: targetProject?.repo?.url || "",
        },
      });
      const newSess = res.session;
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setCurrentSession(newSess);
      toast("New QE session created");
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Switch session
  const handleSelectSession = (id: string) => {
    const s = sessions.find((item) => item.id === id);
    if (s) {
      setActiveSessionId(id);
      setCurrentSession(s);
      setMode(s.mode || "plan");
      if (s.activeAgentId) setActiveAgentId(s.activeAgentId);
    }
  };

  // Switch agent
  const handleSelectAgent = async (agentId: string) => {
    setActiveAgentId(agentId);
    if (currentSession) {
      try {
        await api(`/harness/sessions/${currentSession.id}`, {
          method: "PATCH",
          json: { activeAgentId: agentId },
        });
        setCurrentSession((prev) => (prev ? { ...prev, activeAgentId: agentId } : prev));
      } catch {}
    }
  };

  // Toggle Mode (Plan vs Execute)
  const handleToggleMode = async () => {
    const nextMode = mode === "plan" ? "execute" : "plan";
    setMode(nextMode);
    if (currentSession) {
      try {
        await api(`/harness/sessions/${currentSession.id}`, {
          method: "PATCH",
          json: { mode: nextMode },
        });
        setCurrentSession((prev) => (prev ? { ...prev, mode: nextMode } : prev));
      } catch {}
    }
  };

  // Stop current execution
  const handleStopExecution = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    try {
      if (currentSession) {
        await api("/harness/stop", {
          method: "POST",
          json: { sessionId: currentSession.id },
        });
      }
    } catch {}
    setIsExecuting(false);
    toast("Execution halted by user");
  };

  // Autocomplete Palette Commands List
  const allSlashCommands = [
    ...CORE_COMMANDS.map((c) => ({
      cmd: c.cmd,
      name: c.cmd.slice(1),
      desc: c.desc,
      category: "Core Harness",
    })),
    ...skillsCatalog.map((s) => ({
      cmd: `/${s.name}`,
      name: s.name,
      desc: s.description || `${s.displayName} capability`,
      category: s.category || "Skill",
    })),
  ];

  const filteredCommands = allSlashCommands.filter((c) =>
    c.cmd.toLowerCase().includes(slashFilter.toLowerCase())
  );

  // Handle Input Change for Slash Command Autocomplete
  const handleInputChange = (val: string) => {
    setInputPrompt(val);
    if (val.startsWith("/")) {
      setShowSlashPalette(true);
      setSlashFilter(val);
      setPaletteIndex(0);
    } else {
      setShowSlashPalette(false);
    }
  };

  // Select Slash Command from Palette
  const handleSelectSlashCommand = (cmdStr: string) => {
    setShowSlashPalette(false);
    setInputPrompt("");
    handleSendMessage(cmdStr);
  };

  // Send message with SSE streaming
  const handleSendMessage = async (textToSend?: string) => {
    const prompt = (textToSend || inputPrompt).trim();
    if (!prompt || isExecuting || !currentSession) return;

    setInputPrompt("");
    setShowSlashPalette(false);
    setError("");
    setIsExecuting(true);

    const seq = msgSeqRef.current++;
    const userMessageId = `msg_u_${seq}`;
    const assistantMessageId = `msg_a_${seq + 1}`;

    const userMsg: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: prompt,
      createdAt: 0,
    };

    const asstMsg: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      thinking: "",
      createdAt: 0,
      agentId: activeAgentId,
      toolCalls: [],
    };

    setCurrentSession((prev) => {
      if (!prev) return prev;
      const existing = Array.isArray(prev.messages) ? prev.messages : [];
      return {
        ...prev,
        messages: [...existing, userMsg, asstMsg],
      };
    });

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const chatEndpoint = selectedProjectId
        ? `/api/projects/${selectedProjectId}/harness/chat`
        : "/api/harness/chat";

      const response = await fetch(chatEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        signal: controller.signal,
        body: JSON.stringify({
          sessionId: currentSession.id,
          prompt,
          mode,
          activeAgentId,
          projectId: selectedProjectId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Execution error: HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No readable stream response");

      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;

          const jsonStr = trimmed.slice(6);
          try {
            const ev = JSON.parse(jsonStr);

            if (ev.type === "TEXT_CHUNK") {
              const chunk = ev.chunk;
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = Array.isArray(prev.messages) ? prev.messages : [];
                return {
                  ...prev,
                  messages: msgs.map((m) =>
                    m.id === assistantMessageId ? { ...m, content: m.content + chunk } : m
                  ),
                };
              });
            } else if (ev.type === "THINKING_CHUNK") {
              const chunk = ev.chunk;
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = Array.isArray(prev.messages) ? prev.messages : [];
                return {
                  ...prev,
                  messages: msgs.map((m) =>
                    m.id === assistantMessageId ? { ...m, thinking: (m.thinking || "") + chunk } : m
                  ),
                };
              });
            } else if (ev.type === "TOOL_CALL_STARTED") {
              const newTc = {
                id: ev.toolCallId || `tc_${msgSeqRef.current++}`,
                name: ev.toolName,
                args: ev.args || {},
                status: "running" as const,
              };
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = Array.isArray(prev.messages) ? prev.messages : [];
                return {
                  ...prev,
                  messages: msgs.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, toolCalls: [...(m.toolCalls || []), newTc] }
                      : m
                  ),
                };
              });
            } else if (ev.type === "TOOL_CALL_COMPLETED") {
              const completedId = ev.toolCallId;
              const completedName = ev.toolName;
              const resultStr = JSON.stringify(ev.result, null, 2);
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = Array.isArray(prev.messages) ? prev.messages : [];
                return {
                  ...prev,
                  messages: msgs.map((m) =>
                    m.id === assistantMessageId
                      ? {
                          ...m,
                          toolCalls: (m.toolCalls || []).map((tc) =>
                            tc.id === completedId || tc.name === completedName
                              ? { ...tc, status: "completed" as const, result: resultStr }
                              : tc
                          ),
                        }
                      : m
                  ),
                };
              });
            } else if (ev.type === "AGENT_SWITCHED") {
              setActiveAgentId(ev.toAgentId);
            } else if (ev.type === "TODOS_UPDATED") {
              setCurrentSession((prev) => (prev ? { ...prev, todos: ev.todos } : prev));
            } else if (ev.type === "LEDGER_RECORD_ADDED") {
              setCurrentSession((prev) => (prev ? { ...prev, ledger: [...(prev.ledger || []), ev.record] } : prev));
            } else if (ev.type === "RUN_FINISHED") {
              // Reload gates
              if (selectedProjectId) {
                api(`/projects/${selectedProjectId}/gates`).then(setGates).catch(() => {});
              }
            } else if (ev.type === "ERROR") {
              setError(ev.error || "Harness execution failed");
            }
          } catch {}
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setError(e.message || "Communication with harness failed");
      }
    } finally {
      setIsExecuting(false);
      abortControllerRef.current = null;
      loadSessions();
    }
  };

  const activeAgent = AGENTS.find((a) => a.id === activeAgentId) || AGENTS[0];
  const ActiveAgentIcon = activeAgent.icon;

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] -mt-2">
      {/* 1. Top Harness Hierarchy & Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 pt-1 dark:border-slate-800">
        <div className="flex flex-wrap items-center gap-3">
          {/* Harness Logo & Title */}
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-900 dark:text-white">QE Harness</h1>
                <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400">
                  MAF 2.0
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Orchestration Runtime · Multi-Agent Loops · 8 Quality Gates
              </p>
            </div>
          </div>

          {/* Target Project Selector: "Project in Harness" Hierarchy */}
          <div className="flex items-center gap-1.5 pl-3 border-l border-slate-200 dark:border-slate-800">
            <span className="text-xs font-bold text-slate-500">Target:</span>
            <select
              aria-label="Target Project in Harness"
              className="rounded-lg border border-indigo-500/30 bg-indigo-50/50 px-2.5 py-1 text-xs font-bold text-indigo-900 shadow-sm hover:border-indigo-500 focus:outline-none dark:border-indigo-500/30 dark:bg-indigo-950/40 dark:text-indigo-200"
              value={selectedProjectId}
              onChange={(e) => handleSelectProject(e.target.value)}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Session Switcher */}
          <div className="hidden lg:flex items-center gap-1.5 pl-2">
            <select
              aria-label="Active QE Session"
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800 shadow-sm hover:border-slate-400 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              value={activeSessionId}
              onChange={(e) => handleSelectSession(e.target.value)}
            >
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.messages?.length || 0} msgs)
                </option>
              ))}
            </select>
            <button
              onClick={handleCreateSession}
              title="New Session"
              aria-label="Create new session"
              className="rounded-lg border border-slate-300 p-1 text-slate-600 hover:bg-slate-100 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Right Action Controls */}
        <div className="flex items-center gap-2">
          {/* Autonomous MAF Agent Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <ActiveAgentIcon className={`h-4 w-4 ${activeAgent.color}`} />
            <select
              aria-label="Select Autonomous MAF Agent"
              className="bg-transparent font-medium text-slate-800 focus:outline-none dark:text-slate-200"
              value={activeAgentId}
              onChange={(e) => handleSelectAgent(e.target.value)}
            >
              {AGENTS.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.role})
                </option>
              ))}
            </select>
          </div>

          {/* Mode Toggle Button */}
          <button
            onClick={handleToggleMode}
            title="Toggle Plan vs Execute Mode"
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-bold transition shadow-sm ${
              mode === "execute"
                ? "bg-emerald-600 text-white hover:bg-emerald-500"
                : "border border-indigo-500/30 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:text-indigo-300"
            }`}
          >
            <span className={`h-2 w-2 rounded-full ${mode === "execute" ? "bg-white animate-pulse" : "bg-indigo-500"}`} />
            {mode === "execute" ? "EXECUTE MODE" : "PLAN MODE"}
          </button>

          {/* Centralized Model Status Pill */}
          <Link
            href="/settings"
            title="Centralized LLM Configuration"
            className="hidden md:flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-mono text-slate-700 hover:border-indigo-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
          >
            <span className={`h-2 w-2 rounded-full ${llmConfig?.configured ? "bg-emerald-500" : "bg-rose-500"}`} />
            <span>{llmConfig?.configured ? llmConfig.model : "Setup Model"}</span>
          </Link>

          {/* Inspector Drawer Toggle */}
          <button
            onClick={() => setInspectorOpen(!inspectorOpen)}
            title={inspectorOpen ? "Hide Inspector Pane" : "Show Inspector Pane"}
            aria-label="Toggle inspector pane"
            className={`rounded-lg border border-slate-300 p-1.5 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 ${
              inspectorOpen ? "bg-slate-100 text-indigo-600 dark:bg-slate-800" : ""
            }`}
          >
            {inspectorOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <ErrorNote message={error} />

      {/* 2. Main Harness Split Area */}
      <div className="flex flex-1 min-h-0 gap-3 pt-3 overflow-hidden">
        {/* Interaction / Chat Console */}
        <div className="flex flex-1 flex-col min-w-0 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-slate-800 dark:bg-[#0b1329]">
          {/* Target Project Context HUD Header */}
          {targetProject && (
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/70 px-4 py-2 text-xs dark:border-slate-800 dark:bg-slate-950/40">
              <div className="flex items-center gap-2 truncate">
                <FolderGit2 className="h-3.5 w-3.5 text-indigo-500" />
                <span className="font-bold text-slate-800 dark:text-slate-200 truncate">{targetProject.name}</span>
                <span className="font-mono text-[10px] text-slate-400">({targetProject.id})</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-500">
                <span>{targetProject.repo?.url ? "Repo Connected" : "No repo connected"}</span>
                <span className="rounded bg-indigo-500/10 px-1.5 py-0.5 font-bold text-indigo-600 dark:text-indigo-400">
                  {gates.filter((g) => g.status === "approved").length}/8 Gates
                </span>
              </div>
            </div>
          )}

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {(!currentSession?.messages || currentSession.messages.length === 0) && (
              <div className="flex h-full flex-col items-center justify-center text-center p-6 text-slate-500">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                  <Terminal className="h-6 w-6" />
                </div>
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
                  QE Harness Active for {targetProject?.name || "Target"}
                </h3>
                <p className="max-w-md text-xs text-slate-500 mt-1">
                  Type <span className="font-mono font-bold text-indigo-500">/</span> to browse local skills and commands. Directly execute skills like <span className="font-mono text-indigo-500">/qe-discover</span>, <span className="font-mono text-indigo-500">/qe-plan</span>, or <span className="font-mono text-indigo-500">/security-audit</span>.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-1.5 max-w-lg">
                  {CORE_COMMANDS.slice(0, 6).map((sc) => (
                    <button
                      key={sc.cmd}
                      onClick={() => handleSendMessage(sc.cmd)}
                      className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                    >
                      <span className="font-mono text-indigo-500">{sc.cmd}</span>
                      <span className="text-[11px] text-slate-400">· {sc.desc.split(" ")[0]}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {currentSession?.messages?.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role !== "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white"
                      : "border border-slate-200 bg-white text-slate-900 dark:border-slate-800 dark:bg-slate-900/90 dark:text-slate-100"
                  }`}
                >
                  {/* Thinking Reasoning Accordion */}
                  {msg.thinking && (
                    <details className="mb-3 rounded-lg border border-slate-200 bg-slate-50/80 p-2 text-xs dark:border-slate-800 dark:bg-slate-950/60">
                      <summary className="flex cursor-pointer items-center gap-1.5 font-semibold text-slate-600 dark:text-slate-400">
                        <Brain className="h-3.5 w-3.5 text-indigo-500" />
                        <span>Harness Reasoning Process</span>
                      </summary>
                      <div className="mt-2 font-mono text-[11px] text-slate-600 whitespace-pre-wrap dark:text-slate-400 border-t border-slate-200/50 pt-2 dark:border-slate-800/50">
                        {msg.thinking}
                      </div>
                    </details>
                  )}

                  {/* Tool Call Cards */}
                  {msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div className="mb-3 space-y-1.5">
                      {msg.toolCalls.map((tc) => (
                        <div
                          key={tc.id}
                          className="rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs dark:border-slate-800 dark:bg-slate-950"
                        >
                          <div className="flex items-center justify-between">
                            <span className="flex items-center gap-1.5 font-mono font-semibold text-slate-700 dark:text-slate-300">
                              <Wrench className="h-3.5 w-3.5 text-amber-500" />
                              {tc.name}
                            </span>
                            <span
                              className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                tc.status === "completed"
                                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                  : tc.status === "failed"
                                  ? "bg-rose-500/10 text-rose-600"
                                  : "bg-amber-500/10 text-amber-600 animate-pulse"
                              }`}
                            >
                              {tc.status.toUpperCase()}
                            </span>
                          </div>
                          {tc.result && (
                            <details className="mt-1">
                              <summary className="cursor-pointer text-[10px] text-slate-500">View output</summary>
                              <pre className="mt-1 max-h-32 overflow-x-auto rounded bg-slate-100 p-1.5 text-[10px] font-mono text-slate-800 dark:bg-slate-900 dark:text-slate-200">
                                {tc.result}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Markdown Body */}
                  {msg.content ? (
                    <Markdown>{msg.content}</Markdown>
                  ) : isExecuting && msg.role === "assistant" ? (
                    <div className="flex items-center gap-2 text-xs text-slate-400 py-1">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-500" />
                      <span>Specialist executing in harness sandbox...</span>
                    </div>
                  ) : null}

                  <div className="mt-1 flex items-center justify-end text-[10px] opacity-60">
                    <Clock className="mr-1 h-3 w-3" />
                    {msg.createdAt > 0
                      ? new Date(msg.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                      : "just now"}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Command Pills Bar */}
          <div className="flex flex-wrap items-center gap-1 border-t border-slate-200 bg-slate-50/50 px-3 py-1.5 dark:border-slate-800 dark:bg-slate-950/40">
            <span className="text-[11px] font-bold text-slate-400 mr-1">Skills:</span>
            {["/qe-discover", "/qe-plan", "/qe-generate", "/qe-execute", "/qe-heal", "/security-audit"].map((cmd) => (
              <button
                key={cmd}
                onClick={() => handleSendMessage(cmd)}
                disabled={isExecuting}
                className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700 hover:border-indigo-400 hover:text-indigo-600 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
              >
                {cmd}
              </button>
            ))}
          </div>

          {/* 3. Interactive Input Box with Slash Command Autocomplete Palette */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="relative p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0b1329]"
          >
            {/* Slash Command Autocomplete Floating Popup */}
            {showSlashPalette && filteredCommands.length > 0 && (
              <div className="absolute bottom-full left-3 right-3 mb-2 max-h-60 overflow-y-auto rounded-xl border border-slate-300 bg-white p-1.5 shadow-2xl dark:border-slate-700 dark:bg-slate-900 z-50">
                <div className="px-2 py-1 text-[11px] font-bold text-slate-400 border-b border-slate-200 dark:border-slate-800 flex justify-between">
                  <span>Available Skills & Commands ({filteredCommands.length})</span>
                  <span>Esc to dismiss</span>
                </div>
                <div className="mt-1 space-y-0.5">
                  {filteredCommands.slice(0, 15).map((cmd, idx) => (
                    <button
                      key={cmd.cmd}
                      type="button"
                      onClick={() => handleSelectSlashCommand(cmd.cmd)}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs transition ${
                        idx === paletteIndex
                          ? "bg-indigo-600 text-white"
                          : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold">{cmd.cmd}</span>
                        <span className={`text-[11px] truncate max-w-xs ${idx === paletteIndex ? "text-indigo-200" : "text-slate-400"}`}>
                          · {cmd.desc}
                        </span>
                      </div>
                      <span className={`text-[10px] font-medium ${idx === paletteIndex ? "text-indigo-200" : "text-slate-500"}`}>
                        {cmd.category}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="relative flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 shadow-sm focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 dark:border-slate-700 dark:bg-slate-900">
              <textarea
                ref={textareaRef}
                rows={2}
                value={inputPrompt}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyDown={(e) => {
                  if (showSlashPalette && filteredCommands.length > 0) {
                    if (e.key === "ArrowDown") {
                      e.preventDefault();
                      setPaletteIndex((prev) => (prev + 1) % Math.min(filteredCommands.length, 15));
                      return;
                    } else if (e.key === "ArrowUp") {
                      e.preventDefault();
                      setPaletteIndex((prev) => (prev - 1 + Math.min(filteredCommands.length, 15)) % Math.min(filteredCommands.length, 15));
                      return;
                    } else if (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey)) {
                      e.preventDefault();
                      const chosen = filteredCommands[paletteIndex];
                      if (chosen) {
                        handleSelectSlashCommand(chosen.cmd);
                        return;
                      }
                    } else if (e.key === "Escape") {
                      e.preventDefault();
                      setShowSlashPalette(false);
                      return;
                    }
                  }

                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  } else if (e.key === "Escape" && isExecuting) {
                    handleStopExecution();
                  }
                }}
                placeholder={
                  isExecuting
                    ? "Harness is executing... Press Stop or Esc to halt"
                    : `Type / for skills & commands (/qe-discover, /qe-plan, /security-audit)...`
                }
                className="flex-1 resize-none bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none dark:text-slate-100"
              />

              <div className="flex items-center gap-1.5 shrink-0">
                {isExecuting ? (
                  <Button
                    type="button"
                    variant="danger"
                    onClick={handleStopExecution}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold shadow-sm"
                  >
                    <Square className="h-3.5 w-3.5 fill-current" />
                    <span>Stop</span>
                    <span className="hidden sm:inline font-mono text-[10px] opacity-75">ESC</span>
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    disabled={!inputPrompt.trim() || isExecuting}
                    aria-label="Send to QE Harness"
                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold shadow-sm"
                  >
                    <Send className="h-3.5 w-3.5" />
                    <span>Send</span>
                  </Button>
                )}
              </div>
            </div>
            <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span>Type <kbd className="rounded border px-1 font-mono text-[10px]">/</kbd> for skills · Enter to send · Shift+Enter for newline</span>
              <span>Target: {targetProject?.name}</span>
            </div>
          </form>
        </div>

        {/* 4. Collapsible Inspector Drawer */}
        {inspectorOpen && (
          <aside className="w-80 shrink-0 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-slate-800 dark:bg-[#0b1329]">
            {/* Inspector Navigation Tabs */}
            <div className="flex border-b border-slate-200 bg-slate-50/80 text-xs font-semibold dark:border-slate-800 dark:bg-slate-950/60">
              <button
                onClick={() => setActiveTab("gates")}
                className={`flex-1 py-2.5 text-center transition ${
                  activeTab === "gates"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                8 Gates
              </button>
              <button
                onClick={() => setActiveTab("todos")}
                className={`flex-1 py-2.5 text-center transition ${
                  activeTab === "todos"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Tasks
              </button>
              <button
                onClick={() => setActiveTab("ledger")}
                className={`flex-1 py-2.5 text-center transition ${
                  activeTab === "ledger"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Ledger
              </button>
              <button
                onClick={() => setActiveTab("skills")}
                className={`flex-1 py-2.5 text-center transition ${
                  activeTab === "skills"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Skills
              </button>
            </div>

            {/* Tab 1: 8 Quality Gates for Target Project */}
            {activeTab === "gates" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-1">
                  <span className="font-bold text-slate-700 dark:text-slate-300">
                    Quality Gates ({targetProject?.name})
                  </span>
                  {selectedProjectId && (
                    <Link href={`/projects/${selectedProjectId}/qe`} className="text-[11px] text-indigo-500 hover:underline">
                      QE Studio
                    </Link>
                  )}
                </div>
                {gates.map((g: any) => {
                  const isApproved = g.status === "approved";
                  const isRevise = g.status === "revise";
                  const isRejected = g.status === "rejected";
                  return (
                    <div
                      key={g.gate}
                      className="flex items-center justify-between rounded-lg border border-slate-200 p-2 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50"
                    >
                      <div className="min-w-0 pr-2">
                        <div className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                          G{g.gate} {g.name}
                        </div>
                        <div className="text-[10px] text-slate-400 truncate">
                          {g.decided_by_name || "Pending evaluation"}
                        </div>
                      </div>
                      <span
                        className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          isApproved
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                            : isRevise
                            ? "bg-amber-500/10 text-amber-600"
                            : isRejected
                            ? "bg-rose-500/10 text-rose-600"
                            : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        }`}
                      >
                        {g.status.toUpperCase()}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Tab 2: Todos Checklist */}
            {activeTab === "todos" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-1">
                  <span className="font-bold text-slate-700 dark:text-slate-300">Active Task Ledger</span>
                  <span className="text-[11px] text-slate-400">
                    {currentSession?.todos?.filter((t) => t.completed).length || 0}/
                    {currentSession?.todos?.length || 0}
                  </span>
                </div>
                {currentSession?.todos && currentSession.todos.length > 0 ? (
                  currentSession.todos.map((todo) => (
                    <div
                      key={todo.id}
                      className="flex items-start gap-2 rounded-lg border border-slate-200 p-2 dark:border-slate-800"
                    >
                      <input
                        type="checkbox"
                        checked={todo.completed}
                        readOnly
                        className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                      />
                      <span
                        className={`flex-1 text-slate-700 dark:text-slate-300 ${
                          todo.completed ? "line-through opacity-60" : ""
                        }`}
                      >
                        {todo.text}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-center py-6 text-slate-400">No active tasks in this session.</p>
                )}
              </div>
            )}

            {/* Tab 3: Magentic Ledger */}
            {activeTab === "ledger" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-1">
                  <span className="font-bold text-slate-700 dark:text-slate-300">Magentic Ledger</span>
                  <span className="text-[11px] text-slate-400">{currentSession?.ledger?.length || 0} entries</span>
                </div>
                {currentSession?.ledger && currentSession.ledger.length > 0 ? (
                  currentSession.ledger.map((rec, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-slate-200 p-2 dark:border-slate-800 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{rec.title}</span>
                        <Badge tone="indigo">{rec.type}</Badge>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">{rec.detail}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-center py-6 text-slate-400">No ledger entries recorded yet.</p>
                )}
              </div>
            )}

            {/* Tab 4: Discovered Local Skills with Direct /{name} execution */}
            {activeTab === "skills" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-1">
                  <span className="font-bold text-slate-700 dark:text-slate-300">Discovered Skills</span>
                  <span className="text-[11px] font-mono text-indigo-500">{skillsCatalog.length} Skills</span>
                </div>
                {skillsCatalog.length > 0 ? (
                  skillsCatalog.map((sk, idx) => {
                    const skillName = sk.name || `skill_${idx}`;
                    const displayName = sk.displayName || skillName.replace("-", " ").toUpperCase();
                    const desc = sk.description || `Autonomous ${skillName} skill`;
                    const cmd = `/${skillName}`;
                    return (
                      <div
                        key={skillName}
                        onClick={() => handleSendMessage(cmd)}
                        className="cursor-pointer rounded-lg border border-slate-200 p-2 hover:border-indigo-500/50 hover:bg-indigo-50/20 dark:border-slate-800 dark:hover:bg-slate-900 transition"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                            {cmd}
                          </span>
                          <span className="text-[10px] text-slate-400">v{sk.version || "1.0"}</span>
                        </div>
                        <div className="text-[11px] font-bold text-slate-700 dark:text-slate-300 mt-0.5">
                          {displayName}
                        </div>
                        <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                          {desc}
                        </p>
                      </div>
                    );
                  })
                ) : (
                  <div className="space-y-1.5">
                    {CORE_COMMANDS.map((sc) => (
                      <div
                        key={sc.cmd}
                        onClick={() => handleSendMessage(sc.cmd)}
                        className="cursor-pointer rounded-lg border border-slate-200 p-2 hover:border-indigo-500/50 hover:bg-indigo-50/20 dark:border-slate-800 dark:hover:bg-slate-900 transition"
                      >
                        <span className="font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                          {sc.cmd}
                        </span>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">{sc.desc}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
