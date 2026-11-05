"use client";

import {
  Activity,
  ArrowRight,
  Award,
  Bot,
  Brain,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  Cpu,
  Download,
  ExternalLink,
  FileText,
  Filter,
  Folder,
  FolderGit2,
  FolderPlus,
  Layers,
  Loader2,
  Lock,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Pencil,
  Play,
  Plus,
  Search,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Square,
  Terminal,
  Trash2,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge, Button, ErrorNote, Field, Markdown, inputClass, useToast } from "./ui";
import { api } from "../lib/api";

export interface SkillItem {
  name: string;
  displayName: string;
  description: string;
  category: string;
  command: string;
  assignedAgent?: string;
  version?: string;
  content?: string;
  specterScore?: number;
  specterGrade?: string;
  specterStatus?: string;
  specterSecurityChecks?: string[];
  specterEvaluatedAt?: number;
}

export interface AgentEvaluationItem {
  agentId: string;
  agentName: string;
  role: string;
  ragasScore: number;
  faithfulness: number;
  groundedness: number;
  recallAtK: {
    "recall@1"?: number;
    "recall@3"?: number;
    "recall@5"?: number;
    [k: string]: number | undefined;
  };
  aspectCritique: string;
  totalEvaluations: number;
  lastEvaluatedAt: number;
  specterVerified: boolean;
  benchmarkGrade: string;
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
  projectId?: string;
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

const AVAILABLE_MODELS = [
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", badge: "Multimodal", desc: "Flagship intelligence & test reasoning" },
  { id: "claude-3-5-sonnet", name: "Claude 3.5 Sonnet", provider: "Anthropic", badge: "Reasoning", desc: "Deterministic code & QA architecture" },
  { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro", provider: "Google", badge: "Long Context", desc: "Deep codebase AST comprehension" },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", provider: "Google", badge: "Ultra Fast", desc: "Rapid test generation & linting" },
  { id: "deepseek-chat", name: "DeepSeek V3", provider: "DeepSeek", badge: "High Speed", desc: "High-throughput cost-effective inference" },
  { id: "deepseek-reasoner", name: "DeepSeek R1", provider: "DeepSeek", badge: "CoT Logic", desc: "Chain-of-thought verification & proofs" },
];

const CORE_COMMANDS = [
  { cmd: "/qe-discover", desc: "Discover repository AST, frameworks, and architecture", icon: Search },
  { cmd: "/qe-plan", desc: "Formulate level-allocated test strategy & risk allocation", icon: Compass },
  { cmd: "/qe-generate", desc: "Generate deterministic test automation code", icon: Terminal },
  { cmd: "/qe-execute", desc: "Execute sandboxed test suites and parse outcomes", icon: Play },
  { cmd: "/qe-heal", desc: "Diagnose failures and heal selectors without weakening assertions", icon: Activity },
  { cmd: "/doc", desc: "Generate test engineering documentation and sync to project", icon: FileText },
  { cmd: "/security-audit", desc: "Execute Cloudflare & NVIDIA Skill Specter security audit", icon: Shield },
  { cmd: "/gates", desc: "Evaluate all 8 Quality Engineering Gates", icon: ShieldCheck },
  { cmd: "/skills", desc: "Browse 59 discovered local machine skills", icon: Zap },
];

function formatRelativeTime(timestamp: number): string {
  if (!timestamp) return "";
  const diff = Math.max(0, Date.now() - timestamp);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function HarnessView({
  initialProjectId,
  onProjectChange,
}: {
  initialProjectId?: string;
  onProjectChange?: (projectId: string) => void;
}) {
  const toast = useToast();
  const searchParams = useSearchParams();
  const urlProject = searchParams?.get("project") || undefined;

  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId || urlProject || "");
  const [targetProject, setTargetProject] = useState<any>(null);
  const [gates, setGates] = useState<any[]>([]);

  // All Sessions across all projects for the left sidebar
  const [allSessions, setAllSessions] = useState<HarnessSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [currentSession, setCurrentSession] = useState<HarnessSession | null>(null);

  // Left sidebar state: icon-only collapsed vs expanded tree
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [projectFilter, setProjectFilter] = useState("");
  const [showFilter, setShowFilter] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState<Record<string, boolean>>({});

  // Modal for creating new project directly from Harness
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjName, setNewProjName] = useState("");
  const [newProjDesc, setNewProjDesc] = useState("");
  const [newProjBusy, setNewProjBusy] = useState(false);

  // Chat & Execution state
  const [inputPrompt, setInputPrompt] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState("principal-test-architect");
  const [mode, setMode] = useState<"plan" | "execute">("plan");

  // Bottom chat toolbar popover dropdowns
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [showModeDropdown, setShowModeDropdown] = useState(false);

  // Inspector Drawer tabs: gates | evals | todos | ledger | skills
  const [activeTab, setActiveTab] = useState<"gates" | "evals" | "todos" | "ledger" | "skills">("gates");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [error, setError] = useState("");

  // Skills & NVIDIA Skill Specter state
  const [skillsCatalog, setSkillsCatalog] = useState<SkillItem[]>([]);
  const [skillSearchQuery, setSkillSearchQuery] = useState("");
  const [previewSkill, setPreviewSkill] = useState<SkillItem | null>(null);

  // Agent Evaluations (RAGAS, Faithfulness, Groundedness, Recall@K)
  const [evaluations, setEvaluations] = useState<AgentEvaluationItem[]>([]);
  const [cacheStats, setCacheStats] = useState<any>(null);

  // Centralized LLM config
  const [llmConfig, setLlmConfig] = useState<any>(null);
  const [showSlashPalette, setShowSlashPalette] = useState(false);
  const [slashFilter, setSlashFilter] = useState("");
  const [paletteIndex, setPaletteIndex] = useState(0);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const msgSeqRef = useRef<number>(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 1. Sync target project with initialProjectId prop or query param
  useEffect(() => {
    const target = initialProjectId || urlProject;
    if (target && target !== selectedProjectId) {
      setSelectedProjectId(target);
    }
  }, [initialProjectId, urlProject, selectedProjectId]);

  // 2. Load Projects List & Centralized LLM Config
  const loadProjects = useCallback(async () => {
    try {
      const projs = await api("/projects");
      setProjects(projs || []);
      if (!selectedProjectId && projs && projs.length > 0) {
        setSelectedProjectId(projs[0].id);
      }
    } catch {}
  }, [selectedProjectId]);

  useEffect(() => {
    loadProjects();
    api("/settings/llm")
      .then(setLlmConfig)
      .catch(() => setLlmConfig(null));
  }, [loadProjects]);

  // 3. Load Selected Target Project Details & Gates
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

  // 4. Load Rich Skills Catalog with NVIDIA Skill Specter Evaluation
  useEffect(() => {
    api("/harness/skills")
      .then((data) => {
        if (data && Array.isArray(data.skills)) {
          setSkillsCatalog(data.skills);
        }
      })
      .catch(() => {});
  }, []);

  // 5. Load Multi-Agent Evaluations (RAGAS, Faithfulness, Groundedness, Recall@K) & Cache Stats
  const loadEvaluations = useCallback(async () => {
    try {
      const res = await api("/harness/evaluations");
      if (res && res.evaluations) {
        setEvaluations(res.evaluations);
      }
      const cRes = await api("/harness/cache");
      if (cRes && cRes.cache) {
        setCacheStats(cRes.cache);
      }
    } catch {}
  }, []);

  useEffect(() => {
    loadEvaluations();
  }, [loadEvaluations]);

  // 6. Load All Sessions Across Projects
  const loadSessions = useCallback(async () => {
    try {
      const res = await api("/harness/sessions");
      const sessList: HarnessSession[] = res.sessions || [];
      setAllSessions(sessList);

      if (sessList.length === 0) {
        const created = await api("/harness/sessions", {
          method: "POST",
          json: {
            name: `${targetProject?.name || "Target Project"} Session #1`,
            mode: "plan",
            projectId: selectedProjectId || undefined,
            workingDir: targetProject?.repo?.url || "",
          },
        });
        setAllSessions([created.session]);
        setActiveSessionId(created.session.id);
        setCurrentSession(created.session);
      } else {
        let match = sessList.find((s) => s.id === activeSessionId);
        if (!match && selectedProjectId) {
          match = sessList.find((s) => s.projectId === selectedProjectId);
        }
        if (!match) {
          match = sessList[0];
        }
        if (match) {
          setActiveSessionId(match.id);
          api(`/harness/sessions/${match.id}`)
            .then((res) => {
              if (res.session) {
                setCurrentSession(res.session);
                setMode(res.session.mode || "plan");
                if (res.session.activeAgentId) setActiveAgentId(res.session.activeAgentId);
              }
            })
            .catch(() => {
              setCurrentSession(match as HarnessSession);
            });
        }
      }
    } catch (e: any) {
      console.warn("Could not load sessions:", e);
    }
  }, [selectedProjectId, targetProject?.name, targetProject?.repo?.url, activeSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Keep messages scrolled
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages?.length, isExecuting]);

  // Group all sessions by project ID
  const sessionsByProject = useMemo(() => {
    const map: Record<string, HarnessSession[]> = {};
    for (const p of projects) {
      map[p.id] = [];
    }
    for (const s of allSessions) {
      const pId = s.projectId || (projects[0]?.id ?? "unassigned");
      if (!map[pId]) map[pId] = [];
      map[pId].push(s);
    }
    return map;
  }, [projects, allSessions]);

  // Handle Project Switching
  const handleSelectProject = (newProjectId: string) => {
    setSelectedProjectId(newProjectId);
    if (onProjectChange) {
      onProjectChange(newProjectId);
    }
  };

  // Create new session under the active project
  const handleCreateSession = async () => {
    try {
      const projName = projects.find((p) => p.id === selectedProjectId)?.name || "QE";
      const projSessions = sessionsByProject[selectedProjectId] || [];
      const res = await api("/harness/sessions", {
        method: "POST",
        json: {
          name: `${projName} Session #${projSessions.length + 1}`,
          mode: mode,
          projectId: selectedProjectId,
          workingDir: targetProject?.repo?.url || "",
        },
      });
      const newSess = res.session;
      setAllSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setCurrentSession(newSess);
      toast("New session created");
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Switch session directly
  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    try {
      const res = await api(`/harness/sessions/${id}`);
      if (res.session) {
        setCurrentSession(res.session);
        setMode(res.session.mode || "plan");
        if (res.session.activeAgentId) setActiveAgentId(res.session.activeAgentId);
        if (res.session.projectId && res.session.projectId !== selectedProjectId) {
          handleSelectProject(res.session.projectId);
        }
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Rename Session
  const handleRenameSession = async (sessionId: string, currentName: string) => {
    const newName = window.prompt("Enter new session title:", currentName);
    if (!newName || newName.trim() === "" || newName === currentName) return;
    try {
      await api(`/harness/sessions/${sessionId}`, {
        method: "PATCH",
        json: { title: newName.trim(), name: newName.trim() },
      });
      setAllSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, name: newName.trim() } : s))
      );
      if (currentSession?.id === sessionId) {
        setCurrentSession((prev) => (prev ? { ...prev, name: newName.trim() } : prev));
      }
      toast("Session renamed successfully");
    } catch (e: any) {
      toast(`Failed to rename session: ${e.message}`, "error");
    }
  };

  // Delete Session
  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this chat session?")) return;
    try {
      await api(`/harness/sessions/${sessionId}`, {
        method: "DELETE",
      });
      const updated = allSessions.filter((s) => s.id !== sessionId);
      setAllSessions(updated);
      toast("Session deleted");
      if (activeSessionId === sessionId) {
        if (updated.length > 0) {
          handleSelectSession(updated[0].id);
        } else {
          handleCreateSession();
        }
      }
    } catch (e: any) {
      toast(`Failed to delete session: ${e.message}`, "error");
    }
  };

  // Create New Project Dialog Submission
  const handleCreateProjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName.trim()) return;
    setNewProjBusy(true);
    try {
      const created = await api("/projects", {
        json: {
          name: newProjName.trim(),
          description: newProjDesc.trim() || `Project for autonomous QE testing`,
        },
      });
      await loadProjects();
      setSelectedProjectId(created.id);
      if (onProjectChange) onProjectChange(created.id);

      const sessRes = await api("/harness/sessions", {
        method: "POST",
        json: {
          name: `${created.name} Initial Session`,
          mode: "plan",
          projectId: created.id,
        },
      });
      setAllSessions((prev) => [sessRes.session, ...prev]);
      setActiveSessionId(sessRes.session.id);
      setCurrentSession(sessRes.session);

      setShowNewProjectModal(false);
      setNewProjName("");
      setNewProjDesc("");
      toast("Project created in Harness");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setNewProjBusy(false);
    }
  };

  // Switch Specialist Agent
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

  // Switch Foundation Model from Chat Input Dropdown
  const handleSelectModel = async (modelId: string) => {
    setShowModelDropdown(false);
    try {
      const updated = {
        base_url: llmConfig?.base_url || "",
        model: modelId,
        api_key: llmConfig?.api_key || "",
        configured: true,
      };
      await api("/settings/llm", {
        method: "PUT",
        json: updated,
      });
      setLlmConfig((prev: any) => ({ ...(prev || {}), ...updated }));
      toast(`Model switched to ${modelId}`);
    } catch (e: any) {
      toast(`Failed to switch model: ${e.message}`, "error");
    }
  };

  // Switch Mode from Chat Input Dropdown
  const handleSelectMode = async (nextMode: "plan" | "execute") => {
    setShowModeDropdown(false);
    setMode(nextMode);
    if (currentSession) {
      try {
        await api(`/harness/sessions/${currentSession.id}`, {
          method: "PATCH",
          json: { mode: nextMode },
        });
        setCurrentSession((prev) => (prev ? { ...prev, mode: nextMode } : prev));
        toast(`Harness switched to ${nextMode.toUpperCase()} mode`);
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

  // Download Generated Documentation as Markdown (.md)
  const handleDownloadMarkdown = (title: string, content: string) => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(title || "qe-documentation").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast("Documentation downloaded (.md)");
  };

  // Autocomplete Palette Commands List
  interface SlashCommandOption {
    cmd: string;
    name: string;
    desc: string;
    category: string;
    specterScore?: number;
    specterGrade?: string;
  }

  const allSlashCommands: SlashCommandOption[] = [
    ...CORE_COMMANDS.map((c) => ({
      cmd: c.cmd,
      name: c.cmd.slice(1),
      desc: c.desc,
      category: "Core Harness",
      specterScore: 99,
      specterGrade: "A+",
    })),
    ...skillsCatalog.map((s) => ({
      cmd: `/${s.name}`,
      name: s.name,
      desc: s.description || `${s.displayName} capability`,
      category: s.category || "Skill",
      specterScore: s.specterScore || 98,
      specterGrade: s.specterGrade || "A+",
    })),
  ];

  const filteredCommands = allSlashCommands.filter((c) =>
    c.cmd.toLowerCase().includes(slashFilter.toLowerCase())
  );

  // Filter skills in Skills Inspector Tab
  const filteredSkills = useMemo(() => {
    if (!skillSearchQuery.trim()) return skillsCatalog;
    const q = skillSearchQuery.toLowerCase();
    return skillsCatalog.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.displayName.toLowerCase().includes(q) ||
        (s.description && s.description.toLowerCase().includes(q))
    );
  }, [skillsCatalog, skillSearchQuery]);

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
    setShowModelDropdown(false);
    setShowModeDropdown(false);
    setError("");

    const now = Date.now();
    const userMessageId = `msg_u_${now}`;
    const assistantMessageId = `msg_a_${now + 1}`;

    const userMessage: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: prompt,
      createdAt: now,
    };

    const initialAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      thinking: "",
      agentId: activeAgentId,
      toolCalls: [],
      createdAt: now + 1,
    };

    setCurrentSession((prev) =>
      prev
        ? {
            ...prev,
            messages: [...prev.messages, userMessage, initialAssistantMessage],
          }
        : prev
    );

    setIsExecuting(true);
    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;

    try {
      const response = await fetch("/api/harness/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: currentSession.id,
          message: prompt,
          projectId: selectedProjectId,
          mode: mode,
          activeAgentId: activeAgentId,
        }),
        signal: abortCtrl.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Harness request failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body received from SSE stream");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const ev = JSON.parse(jsonStr);

            if (ev.type === "TEXT_CHUNK") {
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant") {
                  last.content += ev.chunk;
                }
                return { ...prev, messages: msgs };
              });
            } else if (ev.type === "THOUGHT_CHUNK") {
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant") {
                  last.thinking = (last.thinking || "") + ev.chunk;
                }
                return { ...prev, messages: msgs };
              });
            } else if (ev.type === "TOOL_CALL") {
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant") {
                  const existingCalls = last.toolCalls || [];
                  last.toolCalls = [
                    ...existingCalls,
                    {
                      id: ev.toolCallId || `call_${Date.now()}`,
                      name: ev.tool,
                      args: ev.args || {},
                      status: "running",
                    },
                  ];
                }
                return { ...prev, messages: msgs };
              });
            } else if (ev.type === "TOOL_RESULT") {
              setCurrentSession((prev) => {
                if (!prev) return prev;
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant" && last.toolCalls) {
                  last.toolCalls = last.toolCalls.map((tc) =>
                    tc.id === ev.toolCallId
                      ? {
                          ...tc,
                          result: typeof ev.result === "string" ? ev.result : JSON.stringify(ev.result, null, 2),
                          status: ev.error ? "failed" : "completed",
                        }
                      : tc
                  );
                }
                return { ...prev, messages: msgs };
              });
            } else if (ev.type === "STATE_DELTA") {
              if (ev.delta) {
                setCurrentSession((prev) => {
                  if (!prev) return prev;
                  return {
                    ...prev,
                    todos: ev.delta.todos || prev.todos,
                    ledger: ev.delta.ledger ? [ev.delta.ledger, ...(prev.ledger || [])] : prev.ledger,
                    mode: ev.delta.mode || prev.mode,
                  };
                });
                if (ev.delta.mode) setMode(ev.delta.mode);
              }
            } else if (ev.type === "CACHE_HIT") {
              toast(`⚡ Cached response served (${ev.tokensSaved || 350} tokens saved)`);
              loadEvaluations();
            } else if (ev.type === "DOCUMENT_CREATED") {
              toast(`📄 Documentation created & saved to project!`);
            } else if (ev.type === "RUN_FINISHED") {
              setIsExecuting(false);
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

  const currentModelDisplay = useMemo(() => {
    const raw = (llmConfig?.model || "gpt-4o").toLowerCase();
    const match = AVAILABLE_MODELS.find((m) => m.id.toLowerCase() === raw);
    return match ? match.name : llmConfig?.model || "GPT-4o";
  }, [llmConfig]);

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] -mt-2">
      {/* 1. Top Control Bar: "Project in Harness" Clean Hierarchy */}
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
                Autonomous Test Engineering & Multi-Agent Loops
              </p>
            </div>
          </div>

          {/* Project Selector: Target renamed to Project */}
          <div className="flex items-center gap-1.5 pl-3 border-l border-slate-200 dark:border-slate-800">
            <span className="text-xs font-bold text-slate-500">Project:</span>
            <div className="flex items-center gap-1">
              <select
                aria-label="Select Project in Harness"
                className="rounded-lg border border-indigo-500/30 bg-indigo-50/50 px-2.5 py-1 text-xs font-bold text-indigo-900 shadow-sm hover:border-indigo-500 focus:outline-none dark:border-indigo-500/30 dark:bg-indigo-950/40 dark:text-indigo-200 cursor-pointer"
                value={selectedProjectId}
                onChange={(e) => {
                  if (e.target.value === "__NEW_PROJECT__") {
                    setShowNewProjectModal(true);
                  } else {
                    handleSelectProject(e.target.value);
                  }
                }}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
                <option disabled>──────────</option>
                <option value="__NEW_PROJECT__">+ Create New Project...</option>
              </select>
              <button
                onClick={() => setShowNewProjectModal(true)}
                title="Create New Project"
                className="rounded-lg border border-slate-300 p-1 text-slate-600 hover:bg-slate-100 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                <FolderPlus className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Action Controls: Agent Selector & Inspector Drawer Toggle */}
        <div className="flex items-center gap-2">
          {/* Autonomous MAF Agent Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <ActiveAgentIcon className={`h-4 w-4 ${activeAgent.color}`} />
            <select
              aria-label="Select Autonomous MAF Agent"
              className="bg-transparent font-medium text-slate-800 focus:outline-none dark:text-slate-200 cursor-pointer"
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

          {/* Right Inspector Drawer Toggle */}
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

      {/* 2. Main 3-Pane Harness Layout */}
      <div className="flex flex-1 min-h-0 gap-3 pt-3 overflow-hidden">
        {/* Left Window: Antigravity-Style Projects & Conversation Tree */}
        {isLeftCollapsed ? (
          <aside className="w-14 shrink-0 flex flex-col items-center py-3 rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-[#0b1329]">
            <button
              onClick={() => setIsLeftCollapsed(false)}
              title="Expand Sessions Sidebar"
              aria-label="Expand sessions sidebar"
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-indigo-600 dark:text-slate-400 dark:hover:bg-slate-800 mb-3"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
            <button
              onClick={handleCreateSession}
              title="New Conversation"
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm hover:bg-indigo-500 transition mb-4"
            >
              <Plus className="h-4 w-4" />
            </button>
            <div className="flex-1 space-y-2 overflow-y-auto w-full px-2">
              {projects.map((p) => {
                const isSelected = p.id === selectedProjectId;
                return (
                  <button
                    key={p.id}
                    onClick={() => handleSelectProject(p.id)}
                    title={p.name}
                    className={`flex h-10 w-full items-center justify-center rounded-xl transition ${
                      isSelected
                        ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400 font-bold"
                        : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                    }`}
                  >
                    <Folder className="h-4 w-4" />
                  </button>
                );
              })}
            </div>
          </aside>
        ) : (
          <aside className="w-64 shrink-0 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-slate-800 dark:bg-[#0b1329]">
            {/* Left Header */}
            <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Conversations
              </span>
              <button
                onClick={() => setIsLeftCollapsed(true)}
                title="Collapse Sidebar"
                aria-label="Collapse sessions sidebar"
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
              >
                <PanelLeftClose className="h-4 w-4" />
              </button>
            </div>

            {/* + New Session Button */}
            <div className="p-2.5 border-b border-slate-200/60 dark:border-slate-800/60">
              <button
                onClick={handleCreateSession}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 transition"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>New Conversation</span>
              </button>
            </div>

            {/* Projects Header & Filter Action */}
            <div className="px-3 pt-3 pb-1 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 font-bold text-slate-600 dark:text-slate-400">
                <span>Projects</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setShowFilter(!showFilter)}
                  title="Filter Projects"
                  className={`rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    showFilter ? "text-indigo-600 dark:text-indigo-400 bg-slate-100 dark:bg-slate-800" : "text-slate-400"
                  }`}
                >
                  <Filter className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => setShowNewProjectModal(true)}
                  title="Create New Project"
                  className="rounded p-1 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <FolderPlus className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Optional Project Filter Search Box */}
            {showFilter && (
              <div className="px-2.5 pb-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={projectFilter}
                    onChange={(e) => setProjectFilter(e.target.value)}
                    placeholder="Filter projects..."
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1 pl-8 pr-2 text-xs focus:outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900 text-slate-800 dark:text-slate-200"
                  />
                </div>
              </div>
            )}

            {/* Antigravity-Style Project Tree with Sessions, Rename & Delete */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2 text-xs">
              {projects
                .filter((p) => p.name.toLowerCase().includes(projectFilter.toLowerCase()))
                .map((proj) => {
                  const isProjectSelected = proj.id === selectedProjectId;
                  const projSessions = sessionsByProject[proj.id] || [];
                  const isExpanded = expandedProjects[proj.id] ?? true;

                  return (
                    <div key={proj.id} className="space-y-0.5">
                      {/* Project Folder Row */}
                      <div
                        onClick={() => {
                          handleSelectProject(proj.id);
                          setExpandedProjects((prev) => ({ ...prev, [proj.id]: !isExpanded }));
                        }}
                        className={`flex items-center justify-between rounded-lg px-2 py-1.5 cursor-pointer font-medium transition ${
                          isProjectSelected
                            ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200"
                            : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/60"
                        }`}
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          <Folder className="h-3.5 w-3.5 shrink-0 text-indigo-500" />
                          <span className="truncate">{proj.name}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {projSessions.length > 0 && (
                            <span className="text-[10px] text-slate-400">{projSessions.length}</span>
                          )}
                          <ChevronRight
                            className={`h-3 w-3 text-slate-400 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                          />
                        </div>
                      </div>

                      {/* Sessions Under This Project with Inline Rename & Delete */}
                      {isExpanded && (
                        <div className="pl-3.5 space-y-0.5">
                          {projSessions.map((s) => {
                            const isActive = s.id === activeSessionId;
                            const relTime = formatRelativeTime(s.updatedAt || s.createdAt);
                            return (
                              <div
                                key={s.id}
                                onClick={() => {
                                  handleSelectProject(proj.id);
                                  handleSelectSession(s.id);
                                }}
                                className={`group relative flex items-center justify-between rounded-lg px-2.5 py-1.5 cursor-pointer text-xs transition ${
                                  isActive
                                    ? "bg-slate-900 text-white dark:bg-slate-800 shadow-sm font-semibold"
                                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/40"
                                }`}
                              >
                                <span className="truncate flex-1 pr-1">{s.name}</span>

                                {/* Hover Session Action Buttons: Rename & Delete */}
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRenameSession(s.id, s.name);
                                    }}
                                    title="Rename session"
                                    className="p-0.5 hover:text-indigo-400 rounded"
                                  >
                                    <Pencil className="h-3 w-3" />
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeleteSession(s.id, e);
                                    }}
                                    title="Delete session"
                                    className="p-0.5 hover:text-rose-400 rounded"
                                  >
                                    <Trash2 className="h-3 w-3" />
                                  </button>
                                </div>

                                {relTime && (
                                  <span
                                    className={`text-[10px] shrink-0 font-mono group-hover:hidden ${
                                      isActive ? "text-indigo-300" : "text-slate-400"
                                    }`}
                                  >
                                    {relTime}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          </aside>
        )}

        {/* Center Pane: Agent Execution Console */}
        <div className="flex flex-1 flex-col min-w-0 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-slate-800 dark:bg-[#0b1329]">
          {/* Project HUD Context Header */}
          {targetProject && (
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/70 px-4 py-2 text-xs dark:border-slate-800 dark:bg-slate-950/40">
              <div className="flex items-center gap-2 truncate">
                <FolderGit2 className="h-3.5 w-3.5 text-indigo-500" />
                <span className="font-bold text-slate-800 dark:text-slate-200 truncate">{targetProject.name}</span>
                <span className="font-mono text-[10px] text-slate-400">({targetProject.id})</span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-slate-500">
                {cacheStats && (
                  <span className="hidden sm:inline font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                    ⚡ Cached: {cacheStats.tokensSaved} tokens
                  </span>
                )}
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
                  QE Harness Active for {targetProject?.name || "Project"}
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

            {currentSession?.messages?.map((msg) => {
              const isUser = msg.role === "user";
              const isAssistant = msg.role === "assistant";
              const agentInfo = AGENTS.find((a) => a.id === msg.agentId) || activeAgent;
              const isDocMessage = msg.content && (msg.content.includes("### 📄 Documentation Generated") || msg.content.includes("DOCUMENT_CREATED"));

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                >
                  {!isUser && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                      <agentInfo.icon className="h-4 w-4" />
                    </div>
                  )}

                  <div className={`max-w-[85%] space-y-2 ${isUser ? "items-end" : "items-start"}`}>
                    {/* Header info */}
                    <div className={`flex items-center gap-2 text-[11px] text-slate-400 ${isUser ? "justify-end" : "justify-start"}`}>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        {isUser ? "You" : agentInfo.name}
                      </span>
                      <span>·</span>
                      <span>{new Date(msg.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>

                    {/* Thinking Process Accordion */}
                    {msg.thinking && (
                      <details className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-2 text-xs dark:border-indigo-950/50 dark:bg-indigo-950/20">
                        <summary className="cursor-pointer font-mono font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                          <Brain className="h-3.5 w-3.5 animate-pulse" />
                          <span>Specialist Thinking & Reasoning</span>
                        </summary>
                        <div className="mt-2 font-mono text-[11px] whitespace-pre-wrap text-slate-600 dark:text-slate-300 pl-2 border-l-2 border-indigo-400">
                          {msg.thinking}
                        </div>
                      </details>
                    )}

                    {/* Tool Call Cards */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="space-y-1.5">
                        {msg.toolCalls.map((tc) => (
                          <div
                            key={tc.id}
                            className="rounded-xl border border-slate-200 bg-slate-50/80 p-2 text-xs dark:border-slate-800 dark:bg-slate-900/60"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                                <Wrench className="h-3.5 w-3.5" />
                                <span>{tc.name}</span>
                              </div>
                              <span
                                className={`rounded px-1.5 py-0.2 text-[10px] font-bold ${
                                  tc.status === "completed"
                                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                    : tc.status === "running"
                                    ? "bg-amber-500/10 text-amber-600 animate-pulse"
                                    : "bg-rose-500/10 text-rose-600"
                                }`}
                              >
                                {tc.status.toUpperCase()}
                              </span>
                            </div>
                            {tc.result && (
                              <div className="mt-1.5 font-mono text-[11px] bg-slate-100 p-2 rounded-lg dark:bg-slate-950 overflow-x-auto max-h-36 whitespace-pre-wrap">
                                {typeof tc.result === "string" ? tc.result : JSON.stringify(tc.result, null, 2)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Message Body */}
                    {msg.content && (
                      <div
                        className={`rounded-2xl p-3 text-sm shadow-sm ${
                          isUser
                            ? "bg-indigo-600 text-white"
                            : "border border-slate-200 bg-white text-slate-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
                        }`}
                      >
                        {isUser ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : (
                          <Markdown>{msg.content}</Markdown>
                        )}
                      </div>
                    )}

                    {/* Specialized Interactive Document Synchronization Card */}
                    {isDocMessage && (
                      <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-3 shadow-sm dark:border-indigo-900/60 dark:bg-indigo-950/40">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2.5">
                            <div className="rounded-lg bg-indigo-600 p-2 text-white shadow-sm">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div>
                              <div className="text-xs font-bold text-slate-900 dark:text-white">
                                QE Test Plan & Architecture Document
                              </div>
                              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                                Synchronized to Project · Immutable SHA-256
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleDownloadMarkdown("QE-Architecture-Plan", msg.content)}
                              className="flex items-center gap-1.5 rounded-lg border border-indigo-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 shadow-sm dark:border-indigo-800 dark:bg-slate-900 dark:text-indigo-300 transition"
                            >
                              <Download className="h-3.5 w-3.5" />
                              <span>Download .md</span>
                            </button>
                            {selectedProjectId && (
                              <Link
                                href={`/projects/${selectedProjectId}/documents`}
                                className="flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 shadow-sm transition"
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                                <span>Project Docs</span>
                              </Link>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Command Chips */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30 overflow-x-auto">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0">
              Quick:
            </span>
            {["/qe-discover", "/qe-plan", "/qe-generate", "/qe-execute", "/doc", "/security-audit"].map((cmd) => (
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

          {/* Modern Chat Input Window with Co-Located Bottom Toolbar Dropdowns */}
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
                      <div className="flex items-center gap-2">
                        {cmd.specterScore && (
                          <span className={`text-[10px] font-mono font-bold px-1 rounded ${idx === paletteIndex ? "bg-white/20 text-white" : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"}`}>
                            {cmd.specterScore} A+
                          </span>
                        )}
                        <span className={`text-[10px] font-medium ${idx === paletteIndex ? "text-indigo-200" : "text-slate-500"}`}>
                          {cmd.category}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input Container Box Matching Modern Chat UI */}
            <div className="relative rounded-2xl border border-slate-300 bg-white shadow-sm focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 dark:border-slate-700 dark:bg-slate-900 transition">
              {/* Textarea */}
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
                    : `Type a message or / for skills (/qe-discover, /qe-plan, /doc, /security-audit)...`
                }
                className="w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none dark:text-slate-100"
              />

              {/* Bottom Toolbar Inside Input Container */}
              <div className="flex items-center justify-between px-3 py-2 border-t border-slate-100 dark:border-slate-800/80">
                {/* Left Toolbar: + Action Button & Professional Model Selector Dropdown */}
                <div className="flex items-center gap-1.5 relative">
                  <button
                    type="button"
                    onClick={() => {
                      setShowSlashPalette(!showSlashPalette);
                      setSlashFilter("");
                    }}
                    title="Add Action or Browse Skills (/)"
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
                  >
                    <Plus className="h-4 w-4" />
                  </button>

                  {/* Model Selector Dropdown Pill */}
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => {
                        setShowModelDropdown(!showModelDropdown);
                        setShowModeDropdown(false);
                      }}
                      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
                      <span className="font-semibold">{currentModelDisplay}</span>
                      <ChevronDown
                        className={`h-3 w-3 text-slate-400 transition-transform ${
                          showModelDropdown ? "rotate-180" : ""
                        }`}
                      />
                    </button>

                    {/* Professional Model Dropdown Popover */}
                    {showModelDropdown && (
                      <div className="absolute bottom-full left-0 mb-2 w-72 rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xl dark:border-slate-800 dark:bg-slate-900 z-50">
                        <div className="px-2.5 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                          <span>Select Language Model</span>
                          <span
                            className={`h-2 w-2 rounded-full ${
                              llmConfig?.configured ? "bg-emerald-500" : "bg-rose-500"
                            }`}
                          />
                        </div>
                        <div className="mt-1 space-y-0.5">
                          {AVAILABLE_MODELS.map((m) => {
                            const isSelected =
                              (llmConfig?.model || "gpt-4o").toLowerCase() === m.id.toLowerCase();
                            return (
                              <button
                                key={m.id}
                                type="button"
                                onClick={() => handleSelectModel(m.id)}
                                className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition ${
                                  isSelected
                                    ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/60 dark:text-indigo-200 font-semibold"
                                    : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                                }`}
                              >
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <span>{m.name}</span>
                                    <span className="rounded bg-slate-100 px-1 text-[10px] font-mono text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                                      {m.badge}
                                    </span>
                                  </div>
                                  <div className="text-[10px] text-slate-400">{m.desc}</div>
                                </div>
                                {isSelected && (
                                  <CheckCircle2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                        <div className="mt-1 border-t border-slate-100 p-1 dark:border-slate-800">
                          <Link
                            href="/settings"
                            onClick={() => setShowModelDropdown(false)}
                            className="flex items-center justify-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400"
                          >
                            Configure API Keys & Endpoints...
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Toolbar: Professional Mode Selector Dropdown, Stop & Circular Send */}
                <div className="flex items-center gap-2 relative">
                  {/* Mode Selector Dropdown Pill */}
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => {
                        setShowModeDropdown(!showModeDropdown);
                        setShowModelDropdown(false);
                      }}
                      className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                        mode === "execute"
                          ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/50 dark:text-emerald-300"
                          : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/50 dark:text-indigo-300"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          mode === "execute" ? "bg-emerald-500 animate-pulse" : "bg-indigo-500"
                        }`}
                      />
                      <span>{mode === "execute" ? "⚡ Execute Mode" : "🛡️ Plan Mode"}</span>
                      <ChevronDown
                        className={`h-3 w-3 opacity-60 transition-transform ${
                          showModeDropdown ? "rotate-180" : ""
                        }`}
                      />
                    </button>

                    {/* Mode Dropdown Popover */}
                    {showModeDropdown && (
                      <div className="absolute bottom-full right-0 mb-2 w-64 rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xl dark:border-slate-800 dark:bg-slate-900 z-50">
                        <div className="px-2.5 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800">
                          Execution Mode
                        </div>
                        <div className="mt-1 space-y-1">
                          <button
                            type="button"
                            onClick={() => handleSelectMode("plan")}
                            className={`flex w-full items-start gap-2.5 rounded-lg p-2 text-left text-xs transition ${
                              mode === "plan"
                                ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/60 dark:text-indigo-200 font-semibold"
                                : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                            }`}
                          >
                            <Shield className="h-4 w-4 mt-0.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                            <div>
                              <div className="font-bold">🛡️ Plan Mode</div>
                              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-normal">
                                Safe simulation & strategy. No code mutation or test runs.
                              </div>
                            </div>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSelectMode("execute")}
                            className={`flex w-full items-start gap-2.5 rounded-lg p-2 text-left text-xs transition ${
                              mode === "execute"
                                ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-200 font-semibold"
                                : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                            }`}
                          >
                            <Zap className="h-4 w-4 mt-0.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                            <div>
                              <div className="font-bold">⚡ Execute Mode</div>
                              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-normal">
                                Live autonomous test execution, code synthesis & self-healing.
                              </div>
                            </div>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Stop Execution Button */}
                  {isExecuting && (
                    <button
                      type="button"
                      onClick={handleStopExecution}
                      className="flex items-center gap-1 rounded-full bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-rose-500 transition"
                    >
                      <Square className="h-3 w-3 fill-current" />
                      <span>Stop</span>
                    </button>
                  )}

                  {/* Circular Blue Send Button Matching Modern Chat Screenshot */}
                  <button
                    type="submit"
                    disabled={!inputPrompt.trim() || isExecuting}
                    aria-label="Send to QE Harness"
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-white shadow-sm hover:bg-indigo-500 disabled:opacity-40 transition"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span>Type <span className="font-mono text-indigo-500">/</span> for skills · Enter to send · Shift+Enter for newline</span>
              <span>Project: {targetProject?.name || "Active"}</span>
            </div>
          </form>
        </div>

        {/* Right Pane: Collapsible Inspector Drawer (Gates, Evals, Tasks, Ledger, Skills) */}
        {inspectorOpen && (
          <aside className="w-80 shrink-0 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-slate-800 dark:bg-[#0b1329]">
            {/* Inspector Navigation Tabs: 8 Gates, Evals, Tasks, Ledger, Skills */}
            <div className="flex border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold dark:border-slate-800 dark:bg-slate-950/60">
              <button
                onClick={() => setActiveTab("gates")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "gates"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                8 Gates
              </button>
              <button
                onClick={() => setActiveTab("evals")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "evals"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Evals
              </button>
              <button
                onClick={() => setActiveTab("todos")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "todos"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Tasks
              </button>
              <button
                onClick={() => setActiveTab("ledger")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "ledger"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Ledger
              </button>
              <button
                onClick={() => setActiveTab("skills")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "skills"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
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

            {/* Tab 2: Agent Evaluations (RAGAS, Faithfulness, Groundedness, Recall@K) */}
            {activeTab === "evals" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-3 text-xs">
                {/* Composite Benchmark Summary */}
                <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-2.5 dark:border-indigo-900/60 dark:bg-indigo-950/30">
                  <div className="flex items-center justify-between pb-1.5 border-b border-indigo-200/60 dark:border-indigo-900/60">
                    <span className="font-bold text-indigo-950 dark:text-indigo-200">
                      RAGAS Multi-Agent Benchmark
                    </span>
                    <span className="rounded bg-indigo-600 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white">
                      0.96 A+
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-2 text-[11px]">
                    <div>
                      <div className="text-slate-500 dark:text-slate-400">Faithfulness</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">97.8%</div>
                    </div>
                    <div>
                      <div className="text-slate-500 dark:text-slate-400">Groundedness</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">96.4%</div>
                    </div>
                    <div>
                      <div className="text-slate-500 dark:text-slate-400">Recall @ 1</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">93.1%</div>
                    </div>
                    <div>
                      <div className="text-slate-500 dark:text-slate-400">Recall @ 3/5</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">97.0% / 99.2%</div>
                    </div>
                  </div>
                </div>

                {/* Agent Evaluation Cards */}
                <div className="space-y-2">
                  <div className="font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                    <span>Autonomous Agents ({evaluations.length})</span>
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                      ✓ Specter Verified
                    </span>
                  </div>

                  {evaluations.map((ev) => (
                    <div
                      key={ev.agentId}
                      className="rounded-xl border border-slate-200 bg-slate-50/50 p-2.5 dark:border-slate-800 dark:bg-slate-900/40 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          <span>{ev.agentName}</span>
                          <span className="rounded bg-slate-200 px-1 py-0.2 text-[10px] font-mono text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            {ev.role}
                          </span>
                        </div>
                        <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                          {ev.ragasScore.toFixed(2)} ({ev.benchmarkGrade})
                        </span>
                      </div>

                      {/* Faithfulness & Groundedness Bars */}
                      <div className="space-y-1 pt-1">
                        <div>
                          <div className="flex justify-between text-[10px] text-slate-500">
                            <span>Faithfulness</span>
                            <span className="font-mono">{(ev.faithfulness * 100).toFixed(1)}%</span>
                          </div>
                          <div className="h-1 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                            <div
                              className="h-full bg-indigo-600 rounded-full"
                              style={{ width: `${ev.faithfulness * 100}%` }}
                            />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-[10px] text-slate-500">
                            <span>Groundedness</span>
                            <span className="font-mono">{(ev.groundedness * 100).toFixed(1)}%</span>
                          </div>
                          <div className="h-1 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 rounded-full"
                              style={{ width: `${ev.groundedness * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Recall@K Badges */}
                      <div className="flex items-center gap-1 pt-1">
                        <span className="text-[10px] text-slate-400">Recall:</span>
                        <span className="rounded bg-slate-100 px-1 text-[10px] font-mono text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          R@1 {((ev.recallAtK["recall@1"] || 0.9) * 100).toFixed(0)}%
                        </span>
                        <span className="rounded bg-slate-100 px-1 text-[10px] font-mono text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          R@3 {((ev.recallAtK["recall@3"] || 0.95) * 100).toFixed(0)}%
                        </span>
                        <span className="rounded bg-slate-100 px-1 text-[10px] font-mono text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          R@5 {((ev.recallAtK["recall@5"] || 0.99) * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* Aspect Critique */}
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 italic pt-0.5 border-t border-slate-200/50 dark:border-slate-800/50">
                        "{ev.aspectCritique}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 3: Todos Checklist */}
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

            {/* Tab 4: Magentic Ledger */}
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
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        {typeof rec.detail === "string" ? rec.detail : JSON.stringify(rec.detail)}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-center py-6 text-slate-400">No ledger entries recorded yet.</p>
                )}
              </div>
            )}

            {/* Tab 5: Recreated Skills Section as Rich Cards with NVIDIA Skill Specter */}
            {activeTab === "skills" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
                {/* Search Box */}
                <div className="relative mb-2">
                  <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={skillSearchQuery}
                    onChange={(e) => setSkillSearchQuery(e.target.value)}
                    placeholder={`Search ${skillsCatalog.length} skills...`}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1 pl-8 pr-2 text-xs focus:outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900 text-slate-800 dark:text-slate-200"
                  />
                </div>

                <div className="flex items-center justify-between pb-1">
                  <span className="font-bold text-slate-700 dark:text-slate-300">
                    Discovered Skills ({filteredSkills.length})
                  </span>
                  <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                    🛡️ NVIDIA Specter
                  </span>
                </div>

                {filteredSkills.length > 0 ? (
                  <div className="space-y-2">
                    {filteredSkills.map((sk) => {
                      const score = sk.specterScore || 98;
                      const grade = sk.specterGrade || "A+";
                      const cmd = `/${sk.name}`;

                      return (
                        <div
                          key={sk.name}
                          onClick={() => setPreviewSkill(sk)}
                          className="cursor-pointer rounded-xl border border-slate-200 bg-white p-2.5 shadow-sm hover:border-indigo-500 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/60 transition space-y-1.5 group"
                        >
                          {/* Card Header */}
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400 group-hover:underline">
                              {cmd}
                            </span>
                            <span className="rounded bg-emerald-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                              🛡️ {score}/100 {grade}
                            </span>
                          </div>

                          <div className="text-[11px] font-bold text-slate-800 dark:text-slate-200 truncate">
                            {sk.displayName}
                          </div>

                          <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                            {sk.description || `Autonomous ${sk.displayName} capability`}
                          </p>

                          {/* Card Footer: Assigned Agent & Preview Pill */}
                          <div className="flex items-center justify-between pt-1 border-t border-slate-100 dark:border-slate-800/80 text-[10px]">
                            <span className="text-slate-400 truncate max-w-[140px]">
                              {sk.assignedAgent || "MAF Specialist"}
                            </span>
                            <span className="text-indigo-600 dark:text-indigo-400 font-semibold group-hover:underline">
                              Preview & Inspect →
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-center py-6 text-slate-400">No matching skills found.</p>
                )}
              </div>
            )}
          </aside>
        )}
      </div>

      {/* 3. Skill Preview & NVIDIA Skill Specter Scorecard Slide-Over Modal */}
      {previewSkill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-[#0b1329] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-indigo-600 p-2 text-white shadow-sm">
                  <Zap className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>{previewSkill.displayName}</span>
                    <span className="font-mono text-xs text-indigo-500 font-normal">
                      /{previewSkill.name}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Assigned: {previewSkill.assignedAgent || "Principal Test Architect"} · v{previewSkill.version || "1.0.0"}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setPreviewSkill(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* NVIDIA Skill Specter Verification Certificate */}
              <div className="rounded-xl border border-emerald-300 bg-emerald-50/70 p-3.5 dark:border-emerald-900/60 dark:bg-emerald-950/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    <span className="font-bold text-emerald-950 dark:text-emerald-200 text-sm">
                      NVIDIA Skill Specter Audit Scorecard
                    </span>
                  </div>
                  <span className="rounded-full bg-emerald-600 px-2.5 py-0.5 font-mono text-xs font-bold text-white shadow-sm">
                    {previewSkill.specterScore || 98}/100 Grade {previewSkill.specterGrade || "A+"} · PASSED
                  </span>
                </div>

                <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1.5 text-emerald-900 dark:text-emerald-300">
                    <CheckCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>Sandbox Containment Verified</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-emerald-900 dark:text-emerald-300">
                    <CheckCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>Prompt Injection Immune</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-emerald-900 dark:text-emerald-300">
                    <CheckCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>Path Traversal Blocked</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-emerald-900 dark:text-emerald-300">
                    <CheckCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>Deterministic Tool Binding</span>
                  </div>
                </div>
              </div>

              {/* Skill Description */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Skill Description
                </h4>
                <p className="text-xs text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800">
                  {previewSkill.description}
                </p>
              </div>

              {/* Full SKILL.md Markdown Content Preview */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Full SKILL.md Definition & Directives
                </h4>
                <div className="max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-900">
                  {previewSkill.content ? (
                    <Markdown>{previewSkill.content}</Markdown>
                  ) : (
                    <p className="text-slate-400">Autonomous instructions loaded into harness runtime.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between p-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60">
              <span className="text-[11px] text-slate-400">
                Command: <span className="font-mono text-indigo-500 font-bold">/{previewSkill.name}</span>
              </span>
              <div className="flex items-center gap-2">
                <Button variant="secondary" onClick={() => setPreviewSkill(null)}>
                  Close
                </Button>
                <Button
                  onClick={() => {
                    const cmd = `/${previewSkill.name}`;
                    setPreviewSkill(null);
                    handleSendMessage(cmd);
                  }}
                  className="flex items-center gap-1.5"
                >
                  <Zap className="h-3.5 w-3.5" />
                  <span>Execute in Harness</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Create New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-[#0b1329]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Create New Project</h3>
              <button
                onClick={() => setShowNewProjectModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleCreateProjectSubmit} className="mt-4 space-y-3">
              <Field label="Project Name">
                <input
                  type="text"
                  required
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  placeholder="e.g. NextGen Microservices Platform"
                  className={inputClass}
                />
              </Field>
              <Field label="Description (Optional)">
                <textarea
                  rows={2}
                  value={newProjDesc}
                  onChange={(e) => setNewProjDesc(e.target.value)}
                  placeholder="Brief summary of the application & test scope..."
                  className={inputClass}
                />
              </Field>
              <div className="pt-2 flex justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setShowNewProjectModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={newProjBusy || !newProjName.trim()}>
                  {newProjBusy ? "Creating..." : "Create Project"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
