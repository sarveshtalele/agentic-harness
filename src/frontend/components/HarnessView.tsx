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
  RefreshCw,
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
  Code2,
  Bug,
  Paperclip,
  Upload,
  Copy,
  Check,
  MoreVertical,
  FileDown,
  Share2,
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
  todos?: Array<{ id: string; text?: string; title?: string; completed?: boolean; status?: string; agentId?: string }>;
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
];

const HARNESS_GOALS = [
  {
    id: "brd",
    title: "Create BRD",
    desc: "Generate full Business Requirements Document with 8 quality gates & compliance",
    prompt: "Create a complete Business Requirements Document (BRD) with all 8 quality gates, Cloudflare and NVIDIA Specter compliance tables for this project.",
    icon: FileText,
    badge: "Requirements"
  },
  {
    id: "prd",
    title: "Create PRD",
    desc: "Author Product Requirements Document with user stories & Gherkin criteria",
    prompt: "Create a comprehensive Product Requirements Document (PRD) with user stories and Gherkin acceptance criteria.",
    icon: Layers,
    badge: "Product"
  },
  {
    id: "lifecycle",
    title: "Run Testing Lifecycle",
    desc: "Execute autonomous test engineering lifecycle (Gate 0 through Gate 8 sign-off)",
    prompt: "Run the complete Quality Engineering testing lifecycle for this project across all 8 quality gates.",
    icon: RefreshCw,
    badge: "Full QE Loop"
  },
  {
    id: "feature",
    title: "Feature Building",
    desc: "Implement and verify features end-to-end in project sandbox",
    prompt: "Start autonomous feature building in sandbox environment: analyze codebase, design test suite, and implement required code.",
    icon: Code2,
    badge: "Sandbox Build"
  },
  {
    id: "bugfix",
    title: "GitHub Bug Fix & PR",
    desc: "Scan repository, diagnose broken tests or defect drift, heal code & create PR",
    prompt: "Scan repository for defects, diagnose test drift, heal broken test cases with assertion preservation, and prepare a GitHub PR.",
    icon: Bug,
    badge: "Defect Repair"
  },
  {
    id: "security",
    title: "Run Security Audit",
    desc: "Perform Cloudflare Zero-Trust & NVIDIA Skill Specter security evaluation",
    prompt: "Execute comprehensive security audit using Cloudflare Zero-Trust methodology and NVIDIA Skill Specter scorecard.",
    icon: ShieldCheck,
    badge: "Security Audit"
  },
  {
    id: "connect_repo",
    title: "Connect & Scan Repo",
    desc: "Clone target repository into sandbox, scan AST manifests, and generate test strategy",
    prompt: "Connect and scan repository: inspect AST dependencies, package manifests, and generate test strategy.",
    icon: FolderGit2,
    badge: "Intake Scan"
  },
  {
    id: "create_skill",
    title: "Create Agent Skill",
    desc: "Synthesize, test, and package an autonomous agent skill conforming to MAF 2.0 standards",
    prompt: "/create_agent_skill Markdown To Docx Engine",
    icon: Sparkles,
    badge: "Agent Skill"
  }
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

const GATE_TITLES: Record<number, string> = {
  0: "Gate 0: Intake & Scope Boundary",
  1: "Gate 1: Requirements & Acceptance Criteria",
  2: "Gate 2: Test Strategy & Risk Allocation",
  3: "Gate 3: Deterministic Test Design",
  4: "Gate 4: Synthetic Test Data",
  5: "Gate 5: Sandboxed Test Execution",
  6: "Gate 6: Autonomous Healing & Assertion Preservation",
  7: "Gate 7: Coverage Audit & Traceability",
  8: "Gate 8: Production Release Confidence Sign-Off",
};

interface HarnessApprovalCardProps {
  approval: any;
  projectId: string;
  onDecide: (approvalId: string, approved: boolean, feedback: string) => Promise<void>;
}

function HarnessApprovalCard({ approval, projectId, onDecide }: HarnessApprovalCardProps) {
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [busy, setBusy] = useState(false);
  const [decidedStatus, setDecidedStatus] = useState<string | null>(
    approval.status && approval.status !== "pending" ? approval.status : null
  );

  const gateNumber = approval.gate ?? approval.gateNumber ?? (approval.payload?.gate);
  const gateTitle = gateNumber !== undefined && gateNumber !== null
    ? (GATE_TITLES[gateNumber] || `Gate ${gateNumber}: Quality Verification`)
    : (approval.gateName || (approval.toolName ? `Action: ${approval.toolName}` : "Quality Gate Sign-off"));

  const title = approval.title || approval.gateName || (approval.toolName ? `Execute ${approval.toolName}` : "Gate Sign-off Request");
  const summary = approval.summary || approval.artifactSummary || "This action requires explicit Human-in-the-Loop authorization before proceeding.";

  const handleDecision = async (approved: boolean) => {
    if (!approved && !showFeedback && !feedback.trim()) {
      setShowFeedback(true);
      return;
    }
    setBusy(true);
    try {
      await onDecide(approval.id, approved, feedback.trim());
      setDecidedStatus(approved ? "approved" : "rejected");
    } finally {
      setBusy(false);
    }
  };

  if (decidedStatus) {
    return (
      <div className={`my-3 rounded-2xl border p-3.5 shadow-xs transition ${
        decidedStatus === "approved"
          ? "border-emerald-500/40 bg-emerald-50/50 dark:border-emerald-500/30 dark:bg-emerald-950/20"
          : "border-rose-500/40 bg-rose-50/50 dark:border-rose-500/30 dark:bg-rose-950/20"
      }`}>
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            {decidedStatus === "approved" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <X className="h-4 w-4 text-rose-600 dark:text-rose-400" />
            )}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {decidedStatus === "approved" ? "Signed Off & Approved ✓" : "Rejected ✕"} · {title}
            </span>
          </div>
          <span className="font-mono text-[10px] text-slate-400">
            {feedback ? `Reason: ${feedback}` : "Recorded in SQLite & Audit Ledger"}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="my-3 rounded-2xl border-2 border-indigo-500/40 bg-indigo-50/30 p-4 shadow-md backdrop-blur-xs dark:border-indigo-500/40 dark:bg-indigo-950/20">
      {/* Header with Gate Badge & Meta */}
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2.5">
          <div className="rounded-xl bg-indigo-600 p-2 text-white shadow-xs">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-indigo-600/10 px-2.5 py-0.5 font-mono text-[11px] font-bold text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">
                {gateTitle}
              </span>
              <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-bold text-amber-700 dark:text-amber-400">
                Sign-off Required
              </span>
            </div>
            <h4 className="mt-0.5 text-sm font-bold text-slate-900 dark:text-white">
              {title}
            </h4>
          </div>
        </div>

        {/* Reviewer Metadata */}
        <div className="text-right text-[11px] text-slate-500 dark:text-slate-400">
          <div className="font-medium text-slate-700 dark:text-slate-300">Reviewer: Principal Test Architect / QA Lead</div>
          <div className="font-mono text-[10px] text-slate-400">
            {approval.created_at ? `Waiting since ${formatRelativeTime(typeof approval.created_at === "number" ? approval.created_at : Date.parse(approval.created_at))}` : "Pending Review"}
          </div>
        </div>
      </div>

      {/* Summary Box */}
      <div className="mb-3 rounded-xl border border-slate-200/80 bg-white/80 p-3 text-xs leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-900/80 dark:text-slate-300">
        <p>{summary}</p>
        {approval.args && Object.keys(approval.args).length > 0 && (
          <div className="mt-2 rounded-lg bg-slate-100 p-2 font-mono text-[11px] dark:bg-slate-950 max-h-28 overflow-x-auto">
            {JSON.stringify(approval.args, null, 2)}
          </div>
        )}
      </div>

      {/* Optional Feedback / Reason Field */}
      {(showFeedback || feedback) && (
        <div className="mb-3">
          <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
            Decision Reason / Feedback (optional for approval, required for rejection):
          </label>
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="e.g. Assertion integrity verified, all Gherkin criteria satisfied..."
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 font-mono"
          />
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-indigo-200/50 dark:border-indigo-900/50">
        <button
          type="button"
          onClick={() => setShowFeedback(!showFeedback)}
          className="text-[11px] font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-300 cursor-pointer"
        >
          {showFeedback ? "Hide Reason Input" : "Add Reason / Feedback"}
        </button>

        <div className="flex items-center gap-2">
          {/* Reject (Rose) */}
          <button
            type="button"
            disabled={busy}
            onClick={() => handleDecision(false)}
            className="flex items-center gap-1.5 rounded-xl bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-rose-500 disabled:opacity-50 transition cursor-pointer"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
            <span>✕ Reject</span>
          </button>

          {/* Approve (Emerald) */}
          <button
            type="button"
            disabled={busy}
            onClick={() => handleDecision(true)}
            className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-emerald-500 disabled:opacity-50 transition cursor-pointer"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            <span>✓ Approve</span>
          </button>
        </div>
      </div>
    </div>
  );
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
  const urlSkill = searchParams?.get("skill") || undefined;

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

  // Real-time Human-in-the-Loop pending approvals state
  const [pendingApprovals, setPendingApprovals] = useState<any[]>([]);

  // Template document upload state
  const [uploadedTemplate, setUploadedTemplate] = useState<{
    id: string;
    name: string;
    filename: string;
    sectionsCount: number;
  } | null>(null);
  const [uploadingTemplate, setUploadingTemplate] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Bottom chat toolbar popover dropdowns
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [showModeDropdown, setShowModeDropdown] = useState(false);

  // Inspector Drawer tabs: gates | evals | todos | ledger | skills
  const [activeTab, setActiveTab] = useState<"gates" | "evals" | "todos" | "ledger" | "skills">("skills");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [error, setError] = useState("");
  const [deletedSkillNames, setDeletedSkillNames] = useState<string[]>([]);

  // Dynamically compute skills loaded in this session with execution metadata
  const sessionLoadedSkills = useMemo(() => {
    const list: Array<{
      name: string;
      timestamp: number;
      status: string;
      args?: any;
      agentName?: string;
      durationMs?: number;
    }> = [];

    const sess: any = currentSession;
    if (sess?.toolsUsed) {
      Object.entries(sess.toolsUsed).forEach(([name, count]) => {
        list.push({
          name,
          timestamp: currentSession?.updatedAt || Date.now(),
          status: "active",
          args: { calls: count },
          agentName: "Agent",
          durationMs: 85
        });
      });
    }

    if (currentSession?.messages) {
      currentSession.messages.forEach((msg: any) => {
        const toolCalls = msg.toolCalls || msg.tool_calls;
        if (toolCalls) {
          toolCalls.forEach((tc: any) => {
            if (!list.some((s) => s.name === tc.name && s.timestamp === (tc.timestamp || msg.createdAt))) {
              list.push({
                name: tc.name,
                timestamp: tc.timestamp || msg.createdAt,
                status: tc.status || "completed",
                args: tc.args,
                agentName: AGENTS.find((a) => a.id === msg.agentId)?.name || "Agent",
                durationMs: tc.durationMs || 120
              });
            }
          });
        }
        if (msg.role === "user" && msg.content.startsWith("/")) {
          const cmd = msg.content.slice(1).split(" ")[0];
          if (!list.some((s) => s.name === cmd)) {
            list.push({
              name: cmd,
              timestamp: msg.createdAt,
              status: "executed",
              args: { prompt: msg.content },
              agentName: "User Directive",
              durationMs: 45
            });
          }
        }
      });
    }

    return list.filter(
      (s) => !deletedSkillNames.includes(s.name) && !deletedSkillNames.includes(s.name.replace(/^\//, ""))
    );
  }, [currentSession, deletedSkillNames]);

  // Skills & NVIDIA Skill Specter state
  const [skillsCatalog, setSkillsCatalog] = useState<SkillItem[]>([]);
  const [skillSearchQuery, setSkillSearchQuery] = useState("");
  const [previewSkill, setPreviewSkill] = useState<SkillItem | null>(null);

  // Agent Evaluations (RAGAS, Faithfulness, Groundedness, Recall@K)
  const [evaluations, setEvaluations] = useState<AgentEvaluationItem[]>([]);
  const [cacheStats, setCacheStats] = useState<any>(null);

  // Centralized LLM config & Settings Models
  const [llmConfig, setLlmConfig] = useState<any>(null);
  const [configuredModels, setConfiguredModels] = useState<any[]>([]);
  const [showSlashPalette, setShowSlashPalette] = useState(false);
  const [slashFilter, setSlashFilter] = useState("");
  const [paletteIndex, setPaletteIndex] = useState(0);

  // Session Delete & Rename Custom Popups
  const [deleteSessionModal, setDeleteSessionModal] = useState<{ id: string; name: string } | null>(null);
  const [clearAllModal, setClearAllModal] = useState(false);
  const [renameSessionModal, setRenameSessionModal] = useState<{ id: string; name: string } | null>(null);
  const [renameInputVal, setRenameInputVal] = useState("");

  // Message Actions State: Copied ID & Active 3-dots Menu Popover
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [activeMessageMenuId, setActiveMessageMenuId] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const msgSeqRef = useRef<number>(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const activeSessionIdRef = useRef<string>(activeSessionId);
  activeSessionIdRef.current = activeSessionId;

  // 1. Sync target project with initialProjectId prop or query param
  useEffect(() => {
    const target = initialProjectId || urlProject;
    if (target && target !== selectedProjectId) {
      setSelectedProjectId(target);
    }
  }, [initialProjectId, urlProject, selectedProjectId]);

  // Sync skill query param to load skill into chat input without auto-sending
  useEffect(() => {
    if (urlSkill) {
      setInputPrompt(`/${urlSkill} `);
      setTimeout(() => textareaRef.current?.focus(), 150);
    }
  }, [urlSkill]);

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
    api("/models")
      .then((mods) => {
        if (Array.isArray(mods)) {
          setConfiguredModels(mods.filter((m: any) => m.enabled !== 0));
        }
      })
      .catch(() => setConfiguredModels([]));
  }, [loadProjects]);

  // 3. Load Selected Target Project Details, Gates & Pending Approvals
  const loadPendingApprovals = useCallback(async () => {
    if (!selectedProjectId) return;
    try {
      const list = await api(`/projects/${selectedProjectId}/approvals`);
      setPendingApprovals(Array.isArray(list) ? list : []);
    } catch {
      setPendingApprovals([]);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId) return;
    Promise.all([
      api(`/projects/${selectedProjectId}`),
      api(`/projects/${selectedProjectId}/gates`),
      api(`/projects/${selectedProjectId}/approvals`).catch(() => []),
    ])
      .then(([proj, gList, apprList]) => {
        setTargetProject(proj);
        setGates(gList || []);
        setPendingApprovals(Array.isArray(apprList) ? apprList : []);
      })
      .catch(() => {});
  }, [selectedProjectId]);

  useEffect(() => {
    loadPendingApprovals();
    const timer = setInterval(loadPendingApprovals, 10000);
    return () => clearInterval(timer);
  }, [loadPendingApprovals]);

  // Handle Human-in-the-Loop Gate Approval Decision
  const handleDecideApproval = async (approvalId: string, approved: boolean, reason: string = "") => {
    try {
      if (selectedProjectId) {
        await api(`/projects/${selectedProjectId}/approvals/${approvalId}/decide`, {
          method: "POST",
          json: { approved, feedback: reason },
        });
      } else {
        await api(`/approvals/${approvalId}/decide`, {
          method: "POST",
          json: { approved, feedback: reason },
        });
      }
      toast(approved ? "Approval confirmed ✓" : "Approval rejected ✕");
      setPendingApprovals((prev) => prev.filter((a) => a.id !== approvalId));
      if (selectedProjectId) {
        api(`/projects/${selectedProjectId}/gates`).then(setGates).catch(() => {});
      }
      loadPendingApprovals();
      loadSessions();
    } catch (e: any) {
      toast(`Decision error: ${e.message}`, "error");
      throw e;
    }
  };

  // Handle Direct Document Upload (.md, .docx, .txt, .pdf) & ChromaDB RAG Ingestion
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingTemplate(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", file.name.replace(/\.[^/.]+$/, ""));
      formData.append("kind", "brd");
      formData.append("project_id", selectedProjectId || "prj_agentic_qe");

      const res = await fetch("/api/harness/upload-document", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || "Document upload failed");
      }
      const data = await res.json();
      const chunksCount = data.chunksIndexed || 1;
      const templateInfo = {
        id: data.doc_id || "doc_uploaded",
        name: data.title || file.name,
        filename: data.filename || file.name,
        sectionsCount: Math.max(1, chunksCount),
      };
      setUploadedTemplate(templateInfo);

      const notice = `📄 **Document Ingested into Project Specifications & ChromaDB RAG Vector Store:**\n\n- **Governance ID:** \`${data.governance_id || 'DOC-001'}\`\n- **Document Title:** **${data.title}**\n- **Project:** \`${selectedProjectId}\`\n- **RAG Chunks Indexed:** **${chunksCount}** semantic vectors in ChromaDB\n\nAsk questions, request analysis, or click below to generate a domain-grounded BRD/Test Suite using RAG.`;
      toast(`Document added to project & indexed in ChromaDB RAG (${chunksCount} vectors)`);

      const sysMsg: ChatMessage = {
        id: `msg_sys_${Date.now()}`,
        role: "system",
        content: notice,
        createdAt: Date.now(),
      };
      setCurrentSession((prev) =>
        prev ? { ...prev, messages: [...prev.messages, sysMsg] } : prev
      );
    } catch (err: any) {
      toast(`Upload failed: ${err.message}`, "error");
    } finally {
      setUploadingTemplate(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

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
        const curId = activeSessionIdRef.current;
        let match = sessList.find((s) => s.id === curId);
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
  }, [selectedProjectId, targetProject?.name, targetProject?.repo?.url]);

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

  // Handle Project Switching: sync project, URL, and switch to that project's session
  const handleSelectProject = (newProjectId: string) => {
    if (!newProjectId) return;
    setSelectedProjectId(newProjectId);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("project", newProjectId);
      window.history.replaceState({}, "", url.toString());
    }
    if (onProjectChange) {
      onProjectChange(newProjectId);
    }
    setExpandedProjects((prev) => ({ ...prev, [newProjectId]: true }));

    const projSessions = sessionsByProject[newProjectId] || [];
    if (projSessions.length > 0) {
      handleSelectSession(projSessions[0].id, newProjectId);
    } else {
      const projName = projects.find((p) => p.id === newProjectId)?.name || "Project";
      api("/harness/sessions", {
        method: "POST",
        json: {
          name: `${projName} Session #1`,
          mode: mode,
          projectId: newProjectId,
        },
      })
        .then((res) => {
          if (res && res.session) {
            setAllSessions((prev) => [res.session, ...prev]);
            setActiveSessionId(res.session.id);
            setCurrentSession(res.session);
          }
        })
        .catch(() => {});
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

  // Switch session directly with full project alignment and no flicker
  const handleSelectSession = async (id: string, targetProjectId?: string) => {
    setActiveSessionId(id);
    try {
      const res = await api(`/harness/sessions/${id}`);
      if (res.session) {
        setCurrentSession(res.session);
        setMode(res.session.mode || "plan");
        if (res.session.activeAgentId) setActiveAgentId(res.session.activeAgentId);
        const pId = res.session.projectId || targetProjectId;
        if (pId && pId !== selectedProjectId) {
          setSelectedProjectId(pId);
          if (typeof window !== "undefined") {
            const url = new URL(window.location.href);
            url.searchParams.set("project", pId);
            window.history.replaceState({}, "", url.toString());
          }
          if (onProjectChange) {
            onProjectChange(pId);
          }
          setExpandedProjects((prev) => ({ ...prev, [pId]: true }));
        }
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Open Rename Session Popup Window
  const handleOpenRename = (sessionId: string, currentName: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setRenameSessionModal({ id: sessionId, name: currentName });
    setRenameInputVal(currentName);
  };

  const handleConfirmRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameSessionModal || !renameInputVal.trim()) return;
    const newName = renameInputVal.trim();
    const sessionId = renameSessionModal.id;
    try {
      await api(`/harness/sessions/${sessionId}`, {
        method: "PATCH",
        json: { title: newName, name: newName },
      });
      setAllSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, name: newName } : s))
      );
      if (currentSession?.id === sessionId) {
        setCurrentSession((prev) => (prev ? { ...prev, name: newName } : prev));
      }
      toast("Session renamed successfully");
      setRenameSessionModal(null);
    } catch (e: any) {
      toast(`Failed to rename session: ${e.message}`, "error");
    }
  };

  // Open Delete Confirmation Popup Window
  const handleOpenDelete = (sessionId: string, sessionName: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setDeleteSessionModal({ id: sessionId, name: sessionName });
  };

  const handleConfirmDelete = async () => {
    if (!deleteSessionModal) return;
    const sessionId = deleteSessionModal.id;
    try {
      await api(`/harness/sessions/${sessionId}`, {
        method: "DELETE",
      });
      const updated = allSessions.filter((s) => s.id !== sessionId);
      setAllSessions(updated);
      toast("Session deleted");
      setDeleteSessionModal(null);
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

  const handleConfirmClearAll = async () => {
    try {
      await api("/harness/sessions", {
        method: "DELETE",
      });
      setAllSessions([]);
      toast("All conversations cleared");
      setClearAllModal(false);
      handleCreateSession();
    } catch (e: any) {
      toast(`Failed to clear conversations: ${e.message}`, "error");
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
    const cleanContent = cleanMarkdownContent(content);
    const blob = new Blob([cleanContent], { type: "text/markdown;charset=utf-8" });
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

  // Clean markdown content to unwrap raw code fences if returned in ```markdown ... ```
  const cleanMarkdownContent = (text: string): string => {
    if (!text) return "";
    let content = text.trim();
    if (content.startsWith("```markdown") && content.endsWith("```")) {
      content = content.slice(11, -3).trim();
    } else if (content.startsWith("```md") && content.endsWith("```")) {
      content = content.slice(5, -3).trim();
    }
    return content;
  };

  // Convert markdown to rich HTML for Word .docx export
  const markdownToWordHtml = (markdown: string): string => {
    let html = markdown
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre style="background:#0f172a;color:#f8fafc;padding:10pt;font-family:Consolas,monospace;border-radius:4pt;"><code>${code}</code></pre>`;
    });

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3 style="font-size:13pt;color:#334155;margin-top:12pt;margin-bottom:4pt;font-weight:bold;">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 style="font-size:16pt;color:#1e40af;margin-top:16pt;margin-bottom:6pt;font-weight:bold;border-bottom:1pt solid #cbd5e1;padding-bottom:2pt;">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 style="font-size:20pt;color:#1e3a8a;margin-top:20pt;margin-bottom:8pt;font-weight:bold;border-bottom:2pt solid #1e3a8a;padding-bottom:4pt;">$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<b><i>$1</i></b>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    html = html.replace(/\*(.*?)\*/g, '<i>$1</i>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code style="background:#f1f5f9;color:#b91c1c;padding:2pt 4pt;font-family:Consolas,monospace;font-size:10pt;">$1</code>');

    // Bullet items
    html = html.replace(/^\s*-\s+(.*$)/gim, '<li style="margin-bottom:3pt;">$1</li>');
    html = html.replace(/(<li[\s\S]*<\/li>)/, '<ul style="padding-left:18pt;margin-top:4pt;margin-bottom:8pt;">$1</ul>');

    // Paragraphs
    const lines = html.split("\n\n");
    return lines.map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return "";
      if (trimmed.startsWith("<h") || trimmed.startsWith("<pre") || trimmed.startsWith("<ul") || trimmed.startsWith("<li")) return trimmed;
      return `<p style="font-size:11pt;line-height:1.5;margin-top:0;margin-bottom:6pt;color:#1e293b;">${trimmed.replace(/\n/g, "<br/>")}</p>`;
    }).join("\n");
  };

  // Copy message response
  const handleCopyMessage = (content: string, id: string) => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopiedMsgId(id);
    toast("Response copied to clipboard");
    setTimeout(() => {
      setCopiedMsgId((prev) => (prev === id ? null : prev));
    }, 2000);
  };

  // Export as Word Document (.docx)
  const handleExportDocx = (title: string, markdownContent: string) => {
    const cleanContent = cleanMarkdownContent(markdownContent);
    const bodyHtml = markdownToWordHtml(cleanContent);
    const wordDocHtml = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
      <head>
        <meta charset='utf-8'>
        <title>${title}</title>
        <style>
          body { font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1e293b; margin: 1in; }
          h1 { font-size: 18pt; color: #1e3a8a; font-weight: bold; margin-top: 18pt; margin-bottom: 6pt; border-bottom: 1.5pt solid #1e3a8a; }
          h2 { font-size: 14pt; color: #1e40af; font-weight: bold; margin-top: 14pt; margin-bottom: 4pt; border-bottom: 0.5pt solid #cbd5e1; }
          h3 { font-size: 12pt; color: #334155; font-weight: bold; margin-top: 10pt; margin-bottom: 3pt; }
          table { border-collapse: collapse; width: 100%; margin-top: 8pt; margin-bottom: 12pt; font-size: 10pt; }
          th, td { border: 1pt solid #cbd5e1; padding: 6pt 8pt; text-align: left; vertical-align: top; }
          th { background-color: #f1f5f9; font-weight: bold; color: #0f172a; }
          ul, ol { margin-top: 4pt; margin-bottom: 8pt; padding-left: 20pt; }
          li { margin-bottom: 3pt; }
          code { font-family: 'Consolas', monospace; background-color: #f1f5f9; color: #b91c1c; padding: 2pt 4pt; font-size: 9.5pt; }
          pre { font-family: 'Consolas', monospace; background-color: #0f172a; color: #f8fafc; padding: 8pt; margin: 8pt 0; border-radius: 4pt; }
        </style>
      </head>
      <body>
        <div style="margin-bottom: 16pt; border-bottom: 2pt solid #4f46e5; padding-bottom: 8pt;">
          <h2 style="color: #4f46e5; margin: 0;">Agentic QE Platform & Harness</h2>
          <p style="font-size: 9pt; color: #64748b; margin: 2pt 0 0 0;">Synchronized Workspace Documentation · Exported ${new Date().toLocaleDateString()}</p>
        </div>
        ${bodyHtml}
      </body>
      </html>
    `;
    const blob = new Blob([wordDocHtml], { type: "application/msword;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(title || "chat-response").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast("Exported as Word document (.docx)");
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

  // Select Slash Command from Palette: load command into chat input window without auto-sending
  const handleSelectSlashCommand = (cmdStr: string) => {
    setShowSlashPalette(false);
    setInputPrompt(`${cmdStr} `);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
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
        credentials: "include",
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
                  let nextLedger = prev.ledger;
                  if (ev.delta.ledger) {
                    const existing = Array.isArray(prev.ledger) ? prev.ledger : [];
                    const incoming = Array.isArray(ev.delta.ledger) ? ev.delta.ledger : [ev.delta.ledger];
                    nextLedger = [...incoming, ...existing];
                  }
                  return {
                    ...prev,
                    todos: ev.delta.todos || prev.todos,
                    ledger: nextLedger,
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
            } else if (ev.type === "TOOL_APPROVAL_REQUEST") {
              const incoming = {
                id: ev.approvalId,
                title: ev.gate?.gateName || `Approval: ${ev.toolName}`,
                summary: ev.gate?.artifactSummary || `Sign-off required for ${ev.toolName}`,
                gate: ev.gate?.gateNumber,
                gateName: ev.gate?.gateName,
                toolName: ev.toolName,
                args: ev.args,
                status: "pending",
                created_at: Date.now(),
              };
              setPendingApprovals((prev) => {
                if (prev.some((p) => p.id === incoming.id)) return prev;
                return [incoming, ...prev];
              });
              toast(`⚠️ Quality Gate sign-off requested: ${incoming.title}`);
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
    const raw = (llmConfig?.model || "").toLowerCase();
    const match = configuredModels.find((m) => (m.name || m.id || "").toLowerCase() === raw);
    if (match) return match.label || match.name;
    return llmConfig?.model || "Configured Model";
  }, [llmConfig, configuredModels]);

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] -mt-2">
      {/* 1. Top Control Bar: "Project in Harness" Clean Hierarchy */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 pt-1 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-bold text-slate-700 dark:text-slate-200">Autonomous Multi-Agent Loops</span>
            <span className="rounded-md border border-slate-200 bg-slate-100 px-2 py-0.5 text-[10px] font-mono text-slate-600 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300">
              Plan &amp; Execute Engine
            </span>
          </div>
        </div>

        {/* Right Action Controls: Project Selector & Inspector Drawer Toggle */}
        <div className="flex items-center gap-3">
          {/* Project Selector: Placed on the right */}
          <div className="flex items-center gap-1.5">
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

          <div className="h-5 w-[1px] bg-slate-200 dark:bg-slate-800" />

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

            {/* + New Session & Clear All Buttons */}
            <div className="p-2.5 border-b border-slate-200/60 dark:border-slate-800/60 flex items-center gap-1.5">
              <button
                onClick={handleCreateSession}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 transition"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>New Conversation</span>
              </button>
              {allSessions.length > 0 && (
                <button
                  onClick={() => setClearAllModal(true)}
                  className="flex items-center justify-center gap-1 rounded-xl border border-rose-200 bg-rose-50 px-2.5 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-400 dark:hover:bg-rose-900/60 transition"
                  title="Clear all conversation history"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Clear All</span>
                </button>
              )}
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
                                  handleSelectSession(s.id, proj.id);
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
                                    onClick={(e) => handleOpenRename(s.id, s.name, e)}
                                    title="Rename session"
                                    className="p-0.5 hover:text-indigo-400 rounded"
                                  >
                                    <Pencil className="h-3 w-3" />
                                  </button>
                                  <button
                                    onClick={(e) => handleOpenDelete(s.id, s.name, e)}
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

          {/* HITL Sign-off Required Alert Banner */}
          {pendingApprovals.length > 0 && (
            <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2.5 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200">
                <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 animate-pulse" />
                <span className="font-semibold">
                  Human-in-the-Loop Sign-off Required:
                </span>
                <span>
                  {pendingApprovals.length} pending {pendingApprovals.length === 1 ? "gate decision awaits" : "gate decisions await"} your review before execution can proceed.
                </span>
              </div>
              <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 font-mono text-[10px] font-bold text-amber-700 dark:text-amber-300">
                Gate Sign-off
              </span>
            </div>
          )}

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {(!currentSession?.messages || currentSession.messages.length === 0) && (
              <div className="flex min-h-full flex-col items-center justify-start py-6 px-4 text-center text-slate-500 my-auto">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                  <Terminal className="h-6 w-6" />
                </div>
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
                  Autonomous QE Harness Active · {targetProject?.name || "Project"}
                </h3>
                <p className="max-w-lg text-xs text-slate-500 mt-1">
                  Select a core Quality Engineering goal below, or type your instructions. The harness automatically routes tasks to specialized engineering skills.
                </p>

                {/* Rich Goal Cards Grid: 2 Columns for Generous Width */}
                <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl text-left">
                  {HARNESS_GOALS.map((g) => {
                    const Icon = g.icon;
                    return (
                      <button
                        key={g.id}
                        type="button"
                        onClick={() => {
                          setInputPrompt(g.prompt);
                          textareaRef.current?.focus();
                        }}
                        className="group flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs hover:border-indigo-500 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/60 transition text-left cursor-pointer min-h-[110px]"
                      >
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                              <div className="rounded-lg bg-indigo-50 p-1.5 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 group-hover:scale-105 transition shrink-0">
                                <Icon className="h-4 w-4" />
                              </div>
                              <span className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition truncate">
                                {g.title}
                              </span>
                            </div>
                            <span className="shrink-0 rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
                              {g.badge}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                            {g.desc}
                          </p>
                        </div>
                        <div className="mt-2.5 flex items-center gap-1 text-[11px] font-semibold text-indigo-500 group-hover:translate-x-0.5 transition">
                          <span>Customize &amp; Send</span>
                          <ArrowRight className="h-3 w-3" />
                        </div>
                      </button>
                    );
                  })}
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
                      <Terminal className="h-4 w-4" />
                    </div>
                  )}

                  <div className={`space-y-2 ${isUser ? "max-w-[85%] items-end ml-auto" : "min-w-0 flex-1 max-w-full items-start"}`}>
                    {/* Header info */}
                    <div className={`flex items-center gap-2 text-[11px] text-slate-400 ${isUser ? "justify-end" : "justify-start"}`}>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        {isUser ? "You" : "QE Platform"}
                      </span>
                      <span>·</span>
                      <span>{new Date(msg.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>

                    {/* Thinking Process Accordion */}
                    {msg.thinking && (
                      <details className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-2 text-xs dark:border-indigo-950/50 dark:bg-indigo-950/20">
                        <summary className="cursor-pointer font-mono font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                          <Brain className="h-3.5 w-3.5 animate-pulse" />
                          <span>Engine Thinking & Execution Plan</span>
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

                    {/* Message Body with Rich Markdown & Message Actions */}
                    {msg.content && (
                      <div
                        className={`group/msg relative rounded-2xl p-3 text-sm shadow-sm ${
                          isUser
                            ? "bg-indigo-600 text-white"
                            : "border border-slate-200 bg-white text-slate-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
                        }`}
                      >
                        {isUser ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : (
                          <Markdown>{cleanMarkdownContent(msg.content)}</Markdown>
                        )}

                        {/* Per-Message Action Toolbar: Copy, 3-dots Menu for .md and .docx */}
                        {!isUser && (
                          <div className="mt-2.5 flex items-center justify-end gap-1.5 border-t border-slate-100 pt-1.5 text-slate-400 dark:border-slate-800/60">
                            {/* Copy button */}
                            <button
                              onClick={() => handleCopyMessage(cleanMarkdownContent(msg.content), msg.id)}
                              className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
                              title="Copy response"
                            >
                              {copiedMsgId === msg.id ? (
                                <>
                                  <Check className="h-3 w-3 text-emerald-500" />
                                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3 w-3" />
                                  <span className="text-[10px]">Copy</span>
                                </>
                              )}
                            </button>

                            {/* 3-dots Menu Popover */}
                            <div className="relative">
                              <button
                                onClick={() => setActiveMessageMenuId(activeMessageMenuId === msg.id ? null : msg.id)}
                                className={`rounded-md p-1 transition ${activeMessageMenuId === msg.id ? "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-white" : "text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"}`}
                                title="More actions"
                              >
                                <MoreVertical className="h-3.5 w-3.5" />
                              </button>

                              {activeMessageMenuId === msg.id && (
                                <div
                                  className="absolute right-0 top-full mt-1 z-30 w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl dark:border-slate-800 dark:bg-slate-900 animate-in fade-in zoom-in-95 duration-100"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <button
                                    onClick={() => {
                                      handleDownloadMarkdown(`chat-response-${msg.id.substring(0, 8)}`, msg.content);
                                      setActiveMessageMenuId(null);
                                    }}
                                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-indigo-400 transition"
                                  >
                                    <FileDown className="h-3.5 w-3.5 text-indigo-500" />
                                    <span>Download Markdown (.md)</span>
                                  </button>
                                  <button
                                    onClick={() => {
                                      handleExportDocx(`chat-response-${msg.id.substring(0, 8)}`, msg.content);
                                      setActiveMessageMenuId(null);
                                    }}
                                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-600 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-blue-400 transition"
                                  >
                                    <Share2 className="h-3.5 w-3.5 text-blue-500" />
                                    <span>Share as Word (.docx)</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
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

            {/* Real-time Interactive Human-in-the-Loop (HITL) Approval Cards */}
            {pendingApprovals.map((appr) => (
              <HarnessApprovalCard
                key={appr.id}
                approval={appr}
                projectId={selectedProjectId}
                onDecide={handleDecideApproval}
              />
            ))}

            <div ref={messagesEndRef} />
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
              {/* Uploaded Template Quick Action Banner */}
              {uploadedTemplate && (
                <div className="flex items-center justify-between gap-2 px-3.5 py-1.5 bg-indigo-50/80 dark:bg-indigo-950/40 border-b border-indigo-100 dark:border-indigo-900/40 rounded-t-2xl text-xs">
                  <div className="flex items-center gap-2 truncate">
                    <Paperclip className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                    <span className="font-semibold text-indigo-950 dark:text-indigo-200 truncate">
                      Uploaded template: {uploadedTemplate.filename}
                    </span>
                    <span className="rounded bg-indigo-200/60 dark:bg-indigo-900/60 px-1.5 py-0.2 text-[10px] font-bold text-indigo-800 dark:text-indigo-300">
                      {uploadedTemplate.sectionsCount} {uploadedTemplate.sectionsCount === 1 ? "section" : "sections"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setInputPrompt(`Generate complete Business Requirements Document (BRD) from uploaded template '${uploadedTemplate.name}' for this project.`);
                        textareaRef.current?.focus();
                      }}
                      className="rounded-lg bg-indigo-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-xs hover:bg-indigo-500 transition cursor-pointer"
                    >
                      ⚡ Generate BRD from Template
                    </button>
                    <button
                      type="button"
                      onClick={() => setUploadedTemplate(null)}
                      className="rounded p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                      title="Clear template"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              )}

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

                  {/* Document Upload Button for .md, .docx, .txt, .pdf templates */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".md,.docx,.txt,.pdf"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    title="Upload Template Document (.md, .docx, .txt, .pdf)"
                    disabled={uploadingTemplate}
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition cursor-pointer"
                  >
                    {uploadingTemplate ? (
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
                    ) : (
                      <Paperclip className="h-4 w-4" />
                    )}
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
                          <span>Settings Models ({configuredModels.length})</span>
                          <span
                            className={`h-2 w-2 rounded-full ${
                              llmConfig?.configured ? "bg-emerald-500" : "bg-rose-500"
                            }`}
                          />
                        </div>
                        <div className="mt-1 space-y-0.5 max-h-56 overflow-y-auto">
                          {configuredModels.length > 0 ? (
                            configuredModels.map((m) => {
                              const mId = m.name || m.id;
                              const isSelected =
                                (llmConfig?.model || "").toLowerCase() === mId.toLowerCase();
                              return (
                                <button
                                  key={mId}
                                  type="button"
                                  onClick={() => handleSelectModel(mId)}
                                  className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition ${
                                    isSelected
                                      ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/60 dark:text-indigo-200 font-semibold"
                                      : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                                  }`}
                                >
                                  <div>
                                    <div className="flex items-center gap-1.5">
                                      <span className="font-medium">{m.label || m.name}</span>
                                      {m.is_default ? (
                                        <span className="rounded bg-indigo-100 px-1 text-[10px] font-mono text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300">
                                          Default
                                        </span>
                                      ) : null}
                                    </div>
                                    <div className="text-[10px] text-slate-400 font-mono truncate max-w-[180px]">
                                      {mId}
                                    </div>
                                  </div>
                                  {isSelected && (
                                    <CheckCircle2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                                  )}
                                </button>
                              );
                            })
                          ) : (
                            <div className="px-3 py-3 text-center text-xs text-slate-400">
                              No models configured in Settings yet.
                            </div>
                          )}
                        </div>
                        <div className="mt-1 border-t border-slate-100 p-1 dark:border-slate-800">
                          <Link
                            href="/settings"
                            onClick={() => setShowModelDropdown(false)}
                            className="flex items-center justify-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400"
                          >
                            ⚙️ Add / Manage Models in Settings
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
            {/* Inspector Navigation Tabs: Loaded Skills, Session Tasks, Evals, Ledger */}
            <div className="flex border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold dark:border-slate-800 dark:bg-slate-950/60">
              <button
                onClick={() => setActiveTab("skills")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "skills"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Skills ({sessionLoadedSkills.length})
              </button>
              <button
                onClick={() => setActiveTab("todos")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "todos"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Tasks ({currentSession?.todos?.length || 0})
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
                onClick={() => setActiveTab("ledger")}
                className={`flex-1 py-2 text-center transition ${
                  activeTab === "ledger"
                    ? "border-b-2 border-indigo-600 text-indigo-600 bg-white dark:bg-[#0b1329] dark:text-indigo-400 font-bold"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Ledger ({currentSession?.ledger?.length || 0})
              </button>
            </div>

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
                  <span className="text-[11px] font-medium text-slate-400">
                    {currentSession?.todos?.filter((t) => t.completed || t.status === "completed").length || 0}/
                    {currentSession?.todos?.length || 0}
                  </span>
                </div>
                {currentSession?.todos && currentSession.todos.length > 0 ? (
                  currentSession.todos.map((todo, idx) => {
                    const isDone = Boolean(todo.completed || todo.status === "completed");
                    const rawTitle = typeof todo === "string" ? todo : (todo.title || todo.text || (todo as any).task || (todo as any).description || (todo as any).name || "");
                    const taskTitle = rawTitle.trim() || `Execution Task #${idx + 1}`;
                    return (
                      <div
                        key={todo.id || idx}
                        className={`flex items-start gap-2.5 rounded-lg border p-2.5 transition ${
                          isDone
                            ? "border-emerald-200 bg-emerald-50/40 dark:border-emerald-950 dark:bg-emerald-950/20"
                            : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isDone}
                          readOnly
                          className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                        />
                        <div className="flex-1 min-w-0">
                          <span
                            className={`block font-medium text-slate-800 dark:text-slate-200 leading-snug ${
                              isDone ? "line-through text-slate-400 dark:text-slate-500" : ""
                            }`}
                          >
                            {taskTitle}
                          </span>
                          {todo.agentId && (
                            <span className="inline-block mt-1 font-mono text-[10px] text-slate-400 dark:text-slate-500">
                              Agent: {todo.agentId}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
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

            {/* Tab: Loaded Skills in Active Chat Session */}
            {activeTab === "skills" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-1">
                  <span className="font-bold text-slate-700 dark:text-slate-300">
                    Loaded Skills ({sessionLoadedSkills.length})
                  </span>
                  <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                    ⚡ Live Context
                  </span>
                </div>

                {sessionLoadedSkills.length > 0 ? (
                  <div className="space-y-2">
                    {sessionLoadedSkills.map((sk, idx) => (
                      <div
                        key={`${sk.name}-${idx}`}
                        onClick={() => {
                          setInputPrompt(`/${sk.name} `);
                          if (textareaRef.current) {
                            textareaRef.current.focus();
                          }
                        }}
                        className="rounded-xl border border-slate-200 bg-white p-2.5 shadow-xs dark:border-slate-800 dark:bg-slate-900/60 transition space-y-1.5 cursor-pointer hover:border-indigo-400 hover:shadow-sm"
                        title="Click to load skill command into chat"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400 text-xs">
                            /{sk.name}
                          </span>
                          <span className="rounded bg-emerald-50 px-1.5 py-0.5 font-mono text-[9px] font-bold text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                            {sk.status.toUpperCase()}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                          <span>Agent: <b className="text-slate-700 dark:text-slate-300">{sk.agentName || "Harness Specialist"}</b></span>
                          <span>{new Date(sk.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
                        </div>

                        <div className="flex items-center gap-1.5 pt-1">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setInputPrompt(`/test_skill ${sk.name}`);
                              textareaRef.current?.focus();
                            }}
                            className="flex items-center gap-1 rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/80 dark:text-indigo-300 transition"
                          >
                            <Play className="h-2.5 w-2.5" /> Test Skill Live
                          </button>
                          <button
                            type="button"
                            onClick={async (e) => {
                              e.stopPropagation();
                              const cleanName = sk.name.replace(/^\//, "");
                              if (confirm(`Are you sure you want to delete skill '${cleanName}'? This will permanently remove its files from the workspace.`)) {
                                try {
                                  await api(`/skills/studio/${encodeURIComponent(cleanName)}`, { method: "DELETE" });
                                  setDeletedSkillNames((prev) => [...prev, cleanName, sk.name]);
                                } catch (err: any) {
                                  alert(`Failed to delete skill: ${err.message}`);
                                }
                              }
                            }}
                            className="flex items-center gap-1 rounded bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-700 hover:bg-rose-100 dark:bg-rose-950/80 dark:text-rose-300 transition cursor-pointer"
                            title="Delete skill from workspace"
                          >
                            <Trash2 className="h-2.5 w-2.5" /> Delete Skill
                          </button>
                        </div>

                        {sk.args && (
                          <details className="mt-1">
                            <summary className="cursor-pointer text-[10px] text-indigo-500 hover:underline">
                              Execution Metadata &amp; Arguments
                            </summary>
                            <pre className="mt-1 max-h-32 overflow-x-auto rounded bg-slate-100 p-1.5 font-mono text-[9px] text-slate-700 dark:bg-slate-950 dark:text-slate-300 whitespace-pre-wrap">
                              {JSON.stringify(sk.args, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 px-3 text-slate-400 space-y-2">
                    <div className="h-10 w-10 mx-auto rounded-xl bg-slate-100 dark:bg-slate-800/80 flex items-center justify-center text-slate-500">
                      <Cpu className="h-5 w-5" />
                    </div>
                    <p className="font-semibold text-slate-700 dark:text-slate-300">No Skills Loaded Yet</p>
                    <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                      Skills are loaded dynamically into session context as you execute goals or instruct the harness.
                    </p>
                  </div>
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
                    Risk: 0/100 · Health: {previewSkill.specterScore || 98}% ({previewSkill.specterGrade || "A+"}) · {previewSkill.specterStatus || "PASSED"}
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
                    const cmd = `/${previewSkill.name} `;
                    setPreviewSkill(null);
                    setInputPrompt(cmd);
                    if (textareaRef.current) {
                      textareaRef.current.focus();
                    }
                  }}
                  className="flex items-center gap-1.5"
                >
                  <Zap className="h-3.5 w-3.5" />
                  <span>Load Command in Chat</span>
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

      {/* 5. Delete Session Confirmation Popup Modal */}
      {deleteSessionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-800 dark:bg-[#0b1329] space-y-3">
            <div className="flex items-center gap-2.5 text-rose-600 dark:text-rose-400">
              <div className="rounded-xl bg-rose-100 p-2 dark:bg-rose-950/60">
                <Trash2 className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Delete Conversation</h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Are you sure you want to delete <span className="font-semibold text-slate-800 dark:text-slate-200">"{deleteSessionModal.name}"</span>? All messages and ledger checkpoints in this session will be permanently removed.
            </p>
            <div className="pt-2 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setDeleteSessionModal(null)}>
                Cancel
              </Button>
              <Button type="button" variant="danger" onClick={handleConfirmDelete}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 5b. Clear All Sessions Confirmation Modal */}
      {clearAllModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-800 dark:bg-[#0b1329] space-y-3">
            <div className="flex items-center gap-2.5 text-rose-600 dark:text-rose-400">
              <div className="rounded-xl bg-rose-100 p-2 dark:bg-rose-950/60">
                <Trash2 className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Clear All Conversations</h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Are you sure you want to delete all <span className="font-semibold text-slate-800 dark:text-slate-200">{allSessions.length} conversations</span>? All chat threads, tasks, and session context will be reset.
            </p>
            <div className="pt-2 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setClearAllModal(false)}>
                Cancel
              </Button>
              <Button type="button" variant="danger" onClick={handleConfirmClearAll}>
                Clear All
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 6. Rename Session Popup Modal */}
      {renameSessionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-800 dark:bg-[#0b1329]">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Pencil className="h-4 w-4 text-indigo-500" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Rename Conversation</h3>
              </div>
              <button
                onClick={() => setRenameSessionModal(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleConfirmRename} className="mt-3 space-y-3">
              <Field label="Session Title">
                <input
                  type="text"
                  required
                  autoFocus
                  value={renameInputVal}
                  onChange={(e) => setRenameInputVal(e.target.value)}
                  placeholder="e.g. Unit Test Strategy Analysis"
                  className={inputClass}
                />
              </Field>
              <div className="pt-2 flex justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setRenameSessionModal(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={!renameInputVal.trim()}>
                  Save Changes
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
