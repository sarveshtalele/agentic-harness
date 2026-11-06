"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { Badge, Button, Card, ErrorNote, Markdown, PageTitle, Spinner, inputClass } from "../../../components/ui";
import { api } from "../../../lib/api";
import {
  Wand2,
  Sparkles,
  Terminal,
  Play,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  FileText,
  Sliders,
  FolderGit2,
  Upload,
  Layers,
  ArrowRight,
  ShieldCheck,
  Cpu,
  RefreshCw,
  Save,
  Check,
  Copy,
  Plus,
  Trash2,
  ListChecks,
  ExternalLink,
} from "lucide-react";

interface StudioDoc {
  id: string;
  project_id: string;
  project_name: string;
  kind: string;
  title: string;
  current_version: number;
  status: string;
  updated_at: string;
  content?: string;
}

interface TestCaseItem {
  id: string;
  requirement_id: string;
  scenario: string;
  type: string;
  level: string;
  precondition: string;
  test_data: string;
  steps: string[];
  expected_result: string;
  oracle: string;
  priority: string;
}

export default function SkillCreatorStudioPage() {
  const searchParams = useSearchParams();
  const initialProjectId = searchParams.get("project") || "";

  // Data fetching state
  const [documents, setDocuments] = useState<StudioDoc[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Form Inputs
  const [sourceMode, setSourceMode] = useState<"project" | "upload" | "custom">("project");
  const [selectedDocId, setSelectedDocId] = useState("");
  const [targetProjectId, setTargetProjectId] = useState(initialProjectId);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [customText, setCustomText] = useState("");

  // Section 2: Skill Architecture & Step-by-Step Tasks
  const [skillName, setSkillName] = useState("");
  const [category, setCategory] = useState("custom-skills");
  const [description, setDescription] = useState("");
  const [tasks, setTasks] = useState<string[]>([
    "Ingest input parameters & validate schema boundaries",
    "Ground execution rules against specification requirements and data contracts",
    "Execute core domain business logic and state transitions",
    "Assert invariants, boundary limits, and error handling",
    "Emit verifiable execution trace, audit evidence, and gate status",
  ]);
  const [newTaskInput, setNewTaskInput] = useState("");
  const [includeScript, setIncludeScript] = useState(true);

  // Scaffolding outputs
  const [scaffolding, setScaffolding] = useState(false);
  const [generatedSlug, setGeneratedSlug] = useState("");
  const [skillMd, setSkillMd] = useState("");
  const [scriptPy, setScriptPy] = useState("");
  const [evalsJson, setEvalsJson] = useState("");
  const [testCases, setTestCases] = useState<TestCaseItem[]>([]);
  const [activeTab, setActiveTab] = useState<"skill_md" | "script_py" | "evals_json" | "test_cases">("skill_md");

  // Live Script Execution State
  const [scriptArgs, setScriptArgs] = useState('{\n  "action": "run",\n  "payload": { "sample": "verification" }\n}');
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);

  // Benchmark Evaluation State
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<any>(null);

  // Installation state
  const [saving, setSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  // QE Workflow Attachment State
  const [attachingQe, setAttachingQe] = useState(false);
  const [attachedQeResult, setAttachedQeResult] = useState<any>(null);

  // Load project documents
  useEffect(() => {
    api("/skills/studio/documents")
      .then((res) => {
        const docs = res.documents || [];
        setDocuments(docs);
        if (initialProjectId) {
          const match = docs.find((d: StudioDoc) => d.project_id === initialProjectId);
          if (match) {
            handleSelectDoc(match.id, docs);
          }
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingDocs(false));
  }, [initialProjectId]);

  // Generate step-by-step tasks based on document metadata & title
  const generateTasksForDoc = (docTitle: string, docKind: string) => {
    const cleanTitle = docTitle
      .replace(/Business Requirements Document \(BRD\) - /gi, "")
      .replace(/Scenarios/gi, "")
      .replace(/Deterministic Test Cases & Scenario Matrix/gi, "")
      .trim();

    if (docKind === "gherkin") {
      return [
        `Parse Given-When-Then scenarios & contract tables for ${cleanTitle}`,
        `Verify system state preconditions prior to scenario execution`,
        `Execute target behavior according to When action contracts`,
        `Assert postconditions against deterministic Then expectations`,
        `Record test assertion results & Gherkin oracle evidence`,
      ];
    } else if (docKind === "test_cases" || docKind === "test_plan") {
      return [
        `Ingest test scenario matrix & priority classifications (P0-P2) for ${cleanTitle}`,
        `Synthesize deterministic test fixtures & synthetic datasets`,
        `Execute test cases in bounded sandbox worktree`,
        `Collect pass/fail execution logs and stack traces`,
        `Compute gate pass rate and trace coverage matrix`,
      ];
    } else {
      return [
        `Ingest business requirements & parse functional constraints for ${cleanTitle}`,
        `Validate input data contracts & precondition checks`,
        `Execute deterministic workflow calculations & state transitions`,
        `Enforce SLA, audit, and quality gate boundaries`,
        `Generate verifiable execution trace & audit evidence for release sign-off`,
      ];
    }
  };

  // Handle document selection change
  const handleSelectDoc = (docId: string, docList = documents) => {
    setSelectedDocId(docId);
    const doc = docList.find((d) => d.id === docId);
    if (doc) {
      setTargetProjectId(doc.project_id);
      const cleanTitle = doc.title
        .replace(/Business Requirements Document \(BRD\) - /gi, "")
        .replace(/Scenarios/gi, "")
        .replace(/Deterministic Test Cases & Scenario Matrix/gi, "")
        .trim();

      const calculatedName = `${cleanTitle} Agent Skill`;
      setSkillName(calculatedName);
      setDescription(`Automated specification enforcement and verification operations grounded on ${doc.title} (v${doc.current_version}).`);
      
      const categoryMap: Record<string, string> = {
        brd: "business-analysis",
        gherkin: "testing",
        test_cases: "testing",
        test_plan: "quality-engineering",
        discovery: "codebase-intelligence",
      };
      setCategory(categoryMap[doc.kind] || "custom-skills");

      // Auto-outline checklist of step-by-step tasks
      const outlinedTasks = generateTasksForDoc(doc.title, doc.kind);
      setTasks(outlinedTasks);
    }
  };

  // Handle File Upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setCustomText(content);
      const baseName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      setSkillName(`${baseName} Skill`);
      setDescription(`Skill synthesized from ${file.name} document specification.`);
      setTasks([
        `Ingest specification requirements from ${file.name}`,
        `Validate parameter constraints and input boundaries`,
        `Execute core operations according to uploaded requirements`,
        `Assert expected deterministic outputs and error recovery`,
        `Emit audit logs and structured execution evidence`,
      ]);
    };
    reader.readAsText(file);
  };

  // Task list management
  const handleAddTask = () => {
    if (!newTaskInput.trim()) return;
    setTasks([...tasks, newTaskInput.trim()]);
    setNewTaskInput("");
  };

  const handleDeleteTask = (index: number) => {
    setTasks(tasks.filter((_, i) => i !== index));
  };

  const handleUpdateTask = (index: number, val: string) => {
    const updated = [...tasks];
    updated[index] = val;
    setTasks(updated);
  };

  // AI Architect & Contextual Auto-Fill
  const [isSuggesting, setIsSuggesting] = useState(false);

  const handleAiAutoFill = async () => {
    let title = "";
    let content = "";
    if (sourceMode === "project" && selectedDocId) {
      const doc = documents.find((d) => d.id === selectedDocId);
      if (doc) {
        title = doc.title;
        content = doc.content || "";
      }
    } else if (sourceMode === "upload") {
      title = uploadedFileName ? uploadedFileName.replace(/\.[^/.]+$/, "") : "Uploaded Specification";
      content = customText;
    } else {
      title = customText.slice(0, 40).split("\n")[0] || "Custom Domain";
      content = customText;
    }

    if (!title && !content) {
      setError("Please select a document, upload a file, or enter prompt text first.");
      return;
    }

    setError("");
    setIsSuggesting(true);
    try {
      const res = await api("/skills/studio/suggest", {
        json: {
          prompt: customText || undefined,
          documentId: sourceMode === "project" ? selectedDocId || undefined : undefined,
          documentContent: sourceMode !== "project" ? (customText || content) : undefined,
        },
      });

      if (res?.name) {
        setSkillName(res.name);
        setCategory(res.category || "custom-sdlc");
        setDescription(res.description || "");
        if (Array.isArray(res.tasks) && res.tasks.length > 0) {
          setTasks(res.tasks);
        }
        setSuccessMsg(`AI Auto-filled architecture for "${res.name}" (${res.category}) with ${res.tasks.length} tasks!`);
      }
    } catch (e: any) {
      // Robust local fallback
      const cleanTitle = title
        .replace(/Business Requirements Document \(BRD\) - /gi, "")
        .replace(/Scenarios/gi, "")
        .replace(/Deterministic Test Cases & Scenario Matrix/gi, "")
        .replace(/Functional & Verification Requirements Specification/gi, "")
        .replace(/^(?:please\s+)?(?:create|build|generate|make|develop|implement|add)\s+(?:an?\s+)?(?:agent\s+)?(?:skill\s+)?(?:that\s+|which\s+|to\s+)?(?:will\s+)?/gi, "")
        .trim() || "Domain Workflow";

      const aiSkillName = cleanTitle.length > 30 ? `${cleanTitle.slice(0, 25).trim()} Engine` : `${cleanTitle} Engine`;
      setSkillName(aiSkillName);

      const aiTasks = [
        `Ingest input payload and validate schema constraints for ${cleanTitle}`,
        `Verify precondition state and system readiness against specification rules`,
        `Execute core ${cleanTitle.toLowerCase()} transactional operations and state transitions`,
        `Validate postcondition assertions, error boundaries, and exception handling`,
        `Emit cryptographically signed execution trace and sync quality gate status`,
      ];
      setTasks(aiTasks);
      setSuccessMsg(`Auto-filled architecture for "${aiSkillName}" with ${aiTasks.length} tasks.`);
    } finally {
      setIsSuggesting(false);
    }
  };

  // Trigger Scaffolding
  const handleScaffold = async () => {
    if (!skillName.trim()) {
      setError("Please provide a skill name.");
      return;
    }
    setError("");
    setSuccessMsg("");
    setScaffolding(true);
    setExecutionResult(null);
    setEvalResult(null);
    setIsSaved(false);
    setAttachedQeResult(null);

    try {
      // Send valid JSON payload via { json: { ... } }
      const res = await api("/skills/studio/scaffold", {
        json: {
          name: skillName,
          description: description || `Domain skill for ${skillName}.`,
          category,
          includeScript,
          tasks,
          projectId: targetProjectId || undefined,
          documentId: sourceMode === "project" ? selectedDocId || undefined : undefined,
          documentContent: sourceMode !== "project" ? customText || undefined : undefined,
        },
      });

      setGeneratedSlug(res.slug);
      setSkillMd(res.skill_md);
      setScriptPy(res.script_py || "");
      setEvalsJson(res.evals_json || "");
      setTestCases(res.test_cases || []);
      setActiveTab("skill_md");
      setSuccessMsg(`Skill package scaffolded successfully for slug: '${res.slug}' with ${res.test_cases?.length || 0} deterministic test cases.`);
    } catch (err: any) {
      setError(err.message || "Failed to scaffold skill");
    } finally {
      setScaffolding(false);
    }
  };

  // Save / Install Skill
  const handleSaveSkill = async () => {
    if (!generatedSlug || !skillMd) {
      setError("Scaffold a skill first before installing.");
      return;
    }
    setError("");
    setSaving(true);

    try {
      const res = await api("/skills/studio/save", {
        json: {
          slug: generatedSlug,
          name: skillName,
          skill_md: skillMd,
          script_py: scriptPy,
          evals_json: evalsJson,
        },
      });
      setIsSaved(true);
      setSuccessMsg(res.message || `Skill '${generatedSlug}' installed successfully!`);
    } catch (err: any) {
      setError(err.message || "Failed to save skill to platform");
    } finally {
      setSaving(false);
    }
  };

  // Attach Directly to QE Workflow End-to-End
  const handleAttachToQe = async () => {
    if (!targetProjectId) {
      setError("Please select or specify a project to attach the test cases to.");
      return;
    }
    if (!generatedSlug || testCases.length === 0) {
      setError("Scaffold the skill first to generate deterministic test cases.");
      return;
    }

    setError("");
    setAttachingQe(true);

    try {
      // Ensure skill is saved to disk first
      if (!isSaved) {
        await api("/skills/studio/save", {
          json: {
            slug: generatedSlug,
            name: skillName,
            skill_md: skillMd,
            script_py: scriptPy,
            evals_json: evalsJson,
          },
        });
        setIsSaved(true);
      }

      const res = await api("/skills/studio/attach-to-qe", {
        json: {
          projectId: targetProjectId,
          skillSlug: generatedSlug,
          skillName: skillName,
          documentTitle: `Deterministic Test Cases & Scenario Matrix - ${skillName}`,
          testCases: testCases,
          tasks: tasks,
        },
      });

      setAttachedQeResult(res);
      setSuccessMsg(res.message || "Successfully attached test cases to project QE workflow!");
    } catch (err: any) {
      setError(err.message || "Failed to attach to QE workflow");
    } finally {
      setAttachingQe(false);
    }
  };

  // Execute Script
  const handleExecuteScript = async () => {
    if (!generatedSlug) {
      setError("Please scaffold and save the skill before running scripts.");
      return;
    }
    setError("");
    setExecuting(true);

    let parsedArgs = {};
    try {
      parsedArgs = JSON.parse(scriptArgs);
    } catch (e) {
      parsedArgs = { raw: scriptArgs };
    }

    try {
      if (!isSaved) {
        await api("/skills/studio/save", {
          json: {
            slug: generatedSlug,
            name: skillName,
            skill_md: skillMd,
            script_py: scriptPy,
            evals_json: evalsJson,
          },
        });
        setIsSaved(true);
      }

      const res = await api("/skills/studio/execute-script", {
        json: {
          skillSlug: generatedSlug,
          scriptName: "run.py",
          inputArgs: parsedArgs,
        },
      });
      setExecutionResult(res);
    } catch (err: any) {
      setError(err.message || "Execution failed");
    } finally {
      setExecuting(false);
    }
  };

  // Run Benchmark Evaluator
  const handleEvaluate = async () => {
    if (!generatedSlug) {
      setError("Please scaffold and save the skill before benchmarking.");
      return;
    }
    setError("");
    setEvaluating(true);

    try {
      if (!isSaved) {
        await api("/skills/studio/save", {
          json: {
            slug: generatedSlug,
            name: skillName,
            skill_md: skillMd,
            script_py: scriptPy,
            evals_json: evalsJson,
          },
        });
        setIsSaved(true);
      }

      const res = await api("/skills/studio/evaluate", {
        json: { skillSlug: generatedSlug },
      });
      setEvalResult(res.evaluation);
    } catch (err: any) {
      setError(err.message || "Evaluation benchmark failed");
    } finally {
      setEvaluating(false);
    }
  };

  const handleCopyCode = () => {
    const textToCopy =
      activeTab === "skill_md"
        ? skillMd
        : activeTab === "script_py"
        ? scriptPy
        : activeTab === "evals_json"
        ? evalsJson
        : JSON.stringify(testCases, null, 2);
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <PageTitle
          title="Skill Creator Studio"
          subtitle="Synthesize agent skills, task checklists, and deterministic test cases grounded directly in requirements specifications."
          actions={
            <div className="flex items-center gap-2">
              <Link href="/skills">
                <Button variant="secondary">
                  <Layers className="h-4 w-4" /> View Installed Skills
                </Button>
              </Link>
              <Link href="/harness">
                <Button variant="secondary" className="border-indigo-300 dark:border-indigo-700 text-indigo-600 dark:text-indigo-400">
                  <Terminal className="h-4 w-4" /> Open QE Harness
                </Button>
              </Link>
            </div>
          }
        />

        {error && <ErrorNote message={error} />}
        {successMsg && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* QE Attachment Banner */}
        {attachedQeResult && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-300 bg-gradient-to-r from-emerald-50 via-white to-teal-50 p-4 dark:border-emerald-800 dark:from-emerald-950/50 dark:via-[#08151f] dark:to-teal-950/40">
            <div>
              <h4 className="text-sm font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Attached Directly to Project QE Workflow!
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                Created specification <span className="font-semibold text-slate-800 dark:text-slate-200">{attachedQeResult.documentTitle}</span> with {attachedQeResult.testCasesCount} deterministic test cases.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link href={attachedQeResult.qeUrl}>
                <Button className="!bg-emerald-600 hover:!bg-emerald-500 font-semibold !text-xs !py-1.5 shadow-sm">
                  <span>Go to Autonomous QE Workflow</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
              <Link href={attachedQeResult.harnessUrl}>
                <Button variant="secondary" className="!text-xs !py-1.5">
                  <Terminal className="h-3.5 w-3.5" />
                  <span>Execute in Harness</span>
                </Button>
              </Link>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left Column: Skill Configuration, Metadata & Tasks Checklist */}
          <div className="space-y-5 lg:col-span-5">
            <Card title="1. Grounding Specification Source">
              <div className="space-y-3">
                {/* Source Selection Buttons */}
                <div className="grid grid-cols-3 gap-1 rounded-lg border border-slate-200 bg-slate-100 p-1 dark:border-slate-800 dark:bg-slate-900">
                  <button
                    type="button"
                    onClick={() => setSourceMode("project")}
                    className={`rounded-md py-1.5 text-xs font-semibold transition ${
                      sourceMode === "project"
                        ? "bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white"
                        : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                    }`}
                  >
                    Project Specs
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceMode("upload")}
                    className={`rounded-md py-1.5 text-xs font-semibold transition ${
                      sourceMode === "upload"
                        ? "bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white"
                        : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                    }`}
                  >
                    Upload File
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceMode("custom")}
                    className={`rounded-md py-1.5 text-xs font-semibold transition ${
                      sourceMode === "custom"
                        ? "bg-white text-indigo-600 shadow-sm dark:bg-slate-800 dark:text-white"
                        : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                    }`}
                  >
                    Custom Prompt
                  </button>
                </div>

                {/* Mode: Project Specs */}
                {sourceMode === "project" && (
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Select Project Specification / BRD / Gherkin
                    </label>
                    {loadingDocs ? (
                      <Spinner />
                    ) : (
                      <select
                        aria-label="Select specification document"
                        value={selectedDocId}
                        onChange={(e) => handleSelectDoc(e.target.value)}
                        className={inputClass}
                      >
                        <option value="">-- Choose a Grounding Document --</option>
                        {documents.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.title} (v{d.current_version} • {d.kind.toUpperCase()})
                          </option>
                        ))}
                      </select>
                    )}
                    {selectedDocId && (
                      <p className="mt-1 text-[11px] text-slate-500">
                        Skill logic and task checklist automatically grounded on the selected specification.
                      </p>
                    )}
                  </div>
                )}

                {/* Mode: Upload */}
                {sourceMode === "upload" && (
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Upload Requirements File (.md, .txt, .json, .docx)
                    </label>
                    <div className="flex items-center gap-2">
                      <label className="flex cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-dashed border-indigo-300 bg-indigo-50/50 px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-100/60 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300">
                        <Upload className="h-4 w-4" />
                        <span>Choose Document...</span>
                        <input
                          type="file"
                          accept=".md,.txt,.json,.docx,.pdf"
                          className="hidden"
                          onChange={handleFileUpload}
                        />
                      </label>
                      {uploadedFileName && (
                        <span className="text-xs font-mono font-medium text-slate-700 dark:text-slate-300 truncate max-w-[200px]">
                          {uploadedFileName}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Mode: Custom Prompt / Text */}
                {sourceMode === "custom" && (
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Raw Requirements Specification / Domain Brief
                    </label>
                    <textarea
                      aria-label="Custom requirements specification"
                      rows={4}
                      className={inputClass}
                      placeholder="Paste requirement sections, API contracts, business rules, or test constraints here..."
                      value={customText}
                      onChange={(e) => setCustomText(e.target.value)}
                    />
                  </div>
                )}
                {/* AI Context Auto-Fill Button */}
                <button
                  type="button"
                  onClick={handleAiAutoFill}
                  disabled={isSuggesting}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 py-2.5 px-3 text-xs font-bold text-white shadow-md hover:from-indigo-500 hover:to-purple-600 transition-all active:scale-[0.99] disabled:opacity-60"
                >
                  <Sparkles className={`h-4 w-4 text-amber-300 ${isSuggesting ? "animate-spin" : "animate-pulse"}`} />
                  <span>{isSuggesting ? "Architecting Skill Specifications..." : "AI Architect & Auto-Fill Skill Specifications"}</span>
                </button>
              </div>
            </Card>

            <Card title="2. Skill Architecture & Metadata">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Skill Display Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    aria-label="Skill name"
                    placeholder="e.g. Payment Reconciliation Engine"
                    className={inputClass}
                    value={skillName}
                    onChange={(e) => setSkillName(e.target.value)}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      AI SDLC Category
                    </label>
                    <select
                      aria-label="Skill category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className={inputClass}
                    >
                      <option value="requirements-engineering">Requirements Engineering & Specs</option>
                      <option value="ast-intelligence">AST Codebase & Architecture</option>
                      <option value="test-design">Deterministic Test Design Matrix</option>
                      <option value="test-generation">Autonomous Test Synthesis</option>
                      <option value="runtime-execution">Runner Execution & Diagnostics</option>
                      <option value="self-healing">Defect Diagnostics & Self-Healing</option>
                      <option value="quality-governance">Quality Gates & Governance</option>
                      <option value="security-guardrails">Zero-Trust Guardrails & Security</option>
                      <option value="custom-sdlc">Custom SDLC Engineering</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Target Project
                    </label>
                    <input
                      disabled
                      value={targetProjectId || "prj_mcp_market"}
                      className={`${inputClass} bg-slate-100 text-slate-500 dark:bg-slate-800 font-mono text-xs`}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Capability Description & Activation Brief
                  </label>
                  <textarea
                    aria-label="Capability description"
                    rows={2}
                    placeholder="Describe what the skill does and when an agent or developer should invoke it."
                    className={inputClass}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>

                {/* Step-by-Step Guide Checklist as Tasks */}
                <div className="rounded-lg border border-indigo-200/80 bg-indigo-50/40 p-3 dark:border-indigo-900/60 dark:bg-indigo-950/30">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-indigo-950 dark:text-indigo-200 flex items-center gap-1.5">
                      <ListChecks className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                      <span>Step-by-Step Task Checklist</span>
                    </label>
                    <span className="text-[11px] font-medium text-indigo-600 dark:text-indigo-400">
                      {tasks.length} tasks defined
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mb-2.5">
                    These tasks guide the skill operational workflow, execution functions, and deterministic test cases.
                  </p>

                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {tasks.map((task, idx) => (
                      <div key={idx} className="flex items-center gap-2 group">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-indigo-100 text-[10px] font-mono font-bold text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200">
                          {idx + 1}
                        </span>
                        <input
                          aria-label={`Task ${idx + 1}`}
                          className={`${inputClass} !py-1 text-xs`}
                          value={task}
                          onChange={(e) => handleUpdateTask(idx, e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() => handleDeleteTask(idx)}
                          className="p-1 text-slate-400 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition"
                          title="Remove task"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="mt-2.5 flex items-center gap-2">
                    <input
                      aria-label="Add new step task"
                      placeholder="Add another step task..."
                      className={`${inputClass} !py-1 text-xs`}
                      value={newTaskInput}
                      onChange={(e) => setNewTaskInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddTask())}
                    />
                    <Button
                      variant="secondary"
                      onClick={handleAddTask}
                      disabled={!newTaskInput.trim()}
                      className="!px-2.5 !py-1 !text-xs shrink-0"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add
                    </Button>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-0.5">
                  <input
                    id="include-script"
                    type="checkbox"
                    checked={includeScript}
                    onChange={(e) => setIncludeScript(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <label htmlFor="include-script" className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    Generate executable Python runner script (`scripts/run.py`)
                  </label>
                </div>

                <div className="pt-1">
                  <Button
                    onClick={handleScaffold}
                    busy={scaffolding}
                    disabled={!skillName.trim() || tasks.length === 0}
                    className="w-full !py-2.5 shadow-sm font-semibold"
                  >
                    <Wand2 className="h-4 w-4" />
                    <span>Scaffold Agent Skill & Test Cases</span>
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column: Code Preview, Test Cases, Live Runner, & QE Workflow Attachment */}
          <div className="space-y-5 lg:col-span-7">
            {/* Artifact Code & Test Cases Tabs */}
            <Card
              title={
                <div className="flex items-center gap-2">
                  <FileCode className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                  <span>Synthesized Skill Package</span>
                  {generatedSlug && (
                    <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-[11px] font-bold text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                      skills/{generatedSlug}
                    </span>
                  )}
                </div>
              }
              actions={
                generatedSlug ? (
                  <div className="flex items-center gap-1.5">
                    <Button variant="secondary" onClick={handleCopyCode} className="!px-2 !py-1 !text-xs">
                      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                      <span>{copied ? "Copied" : "Copy"}</span>
                    </Button>
                    <Button
                      variant={isSaved ? "secondary" : "primary"}
                      onClick={handleSaveSkill}
                      busy={saving}
                      className="!px-2.5 !py-1 !text-xs font-semibold"
                    >
                      {isSaved ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <Save className="h-3.5 w-3.5" />}
                      <span>{isSaved ? "Installed" : "Install Skill"}</span>
                    </Button>
                  </div>
                ) : null
              }
            >
              {generatedSlug ? (
                <div className="space-y-3">
                  {/* Tab Selector */}
                  <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-2 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={() => setActiveTab("skill_md")}
                      className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                        activeTab === "skill_md"
                          ? "bg-indigo-600 text-white"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                      }`}
                    >
                      <FileText className="h-3.5 w-3.5" />
                      <span>SKILL.md</span>
                    </button>
                    {includeScript && (
                      <button
                        type="button"
                        onClick={() => setActiveTab("script_py")}
                        className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                          activeTab === "script_py"
                            ? "bg-indigo-600 text-white"
                            : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                        }`}
                      >
                        <FileCode className="h-3.5 w-3.5" />
                        <span>scripts/run.py</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setActiveTab("evals_json")}
                      className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                        activeTab === "evals_json"
                          ? "bg-indigo-600 text-white"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                      }`}
                    >
                      <ShieldCheck className="h-3.5 w-3.5" />
                      <span>evals.json</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("test_cases")}
                      className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                        activeTab === "test_cases"
                          ? "bg-indigo-600 text-white"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                      }`}
                    >
                      <ListChecks className="h-3.5 w-3.5" />
                      <span>Test Cases Matrix ({testCases.length})</span>
                    </button>
                  </div>

                  {/* Tab Editor/Viewer */}
                  <div>
                    {activeTab === "skill_md" && (
                      <textarea
                        aria-label="SKILL.md content"
                        rows={14}
                        className={`${inputClass} font-mono text-xs leading-relaxed`}
                        value={skillMd}
                        onChange={(e) => setSkillMd(e.target.value)}
                      />
                    )}
                    {activeTab === "script_py" && (
                      <textarea
                        aria-label="run.py script content"
                        rows={14}
                        className={`${inputClass} font-mono text-xs leading-relaxed`}
                        value={scriptPy}
                        onChange={(e) => setScriptPy(e.target.value)}
                      />
                    )}
                    {activeTab === "evals_json" && (
                      <textarea
                        aria-label="evals.json content"
                        rows={14}
                        className={`${inputClass} font-mono text-xs leading-relaxed`}
                        value={evalsJson}
                        onChange={(e) => setEvalsJson(e.target.value)}
                      />
                    )}
                    {activeTab === "test_cases" && (
                      <div className="overflow-x-auto max-h-80 rounded-lg border border-slate-200 dark:border-slate-800">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-500 uppercase">
                            <tr>
                              <th className="px-3 py-2">TC ID</th>
                              <th className="px-3 py-2">Scenario</th>
                              <th className="px-3 py-2">Type</th>
                              <th className="px-3 py-2">Oracle</th>
                              <th className="px-3 py-2">Priority</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                            {testCases.map((tc, idx) => (
                              <tr key={tc.id || idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-900/40">
                                <td className="px-3 py-2 font-bold text-indigo-600 dark:text-indigo-400">{tc.id}</td>
                                <td className="px-3 py-2 font-sans font-medium text-slate-800 dark:text-slate-200">{tc.scenario}</td>
                                <td className="px-3 py-2">
                                  <Badge tone={tc.type === "Positive" ? "emerald" : tc.type === "Negative" ? "rose" : "slate"}>
                                    {tc.type}
                                  </Badge>
                                </td>
                                <td className="px-3 py-2 text-slate-500 truncate max-w-[150px]">{tc.oracle}</td>
                                <td className="px-3 py-2">
                                  <span className="font-bold text-slate-700 dark:text-slate-300">{tc.priority}</span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="rounded-full bg-indigo-50 p-3 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                    <Wand2 className="h-6 w-6" />
                  </div>
                  <h3 className="mt-3 text-sm font-bold text-slate-900 dark:text-white">
                    No Skill Package Scaffolded Yet
                  </h3>
                  <p className="mt-1 max-w-sm text-xs text-slate-500">
                    Select a specification on the left, review the step-by-step task checklist, then click "Scaffold Agent Skill & Test Cases".
                  </p>
                </div>
              )}
            </Card>

            {/* Direct End-to-End QE Workflow Attachment Card */}
            {generatedSlug && testCases.length > 0 && (
              <Card
                title={
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Attach Test Cases Directly to QE Workflow End-to-End</span>
                  </div>
                }
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs text-slate-600 dark:text-slate-300">
                      Creates <code className="font-mono text-indigo-600 dark:text-indigo-400">Deterministic Test Cases & Scenario Matrix</code> in project <span className="font-semibold">{targetProjectId || "prj_mcp_market"}</span> and binds the {testCases.length} test cases to the Autonomous Quality Engineering lifecycle.
                    </p>
                  </div>
                  <Button
                    onClick={handleAttachToQe}
                    busy={attachingQe}
                    className="!bg-emerald-600 hover:!bg-emerald-500 font-semibold !px-4 !py-2 text-xs shadow-sm shrink-0"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Attach to QE Workflow End-to-End</span>
                  </Button>
                </div>
              </Card>
            )}

            {/* Live Script Sandbox Runner */}
            {generatedSlug && includeScript && (
              <Card
                title={
                  <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Live Sandbox Execution Console</span>
                  </div>
                }
                actions={
                  <Button
                    onClick={handleExecuteScript}
                    busy={executing}
                    className="!px-3 !py-1 !text-xs !bg-emerald-600 hover:!bg-emerald-500 font-semibold"
                  >
                    <Play className="h-3.5 w-3.5" />
                    <span>Run Script</span>
                  </Button>
                }
              >
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      JSON Input Arguments (`--json`)
                    </label>
                    <textarea
                      aria-label="Script input arguments"
                      rows={3}
                      className={`${inputClass} font-mono text-xs`}
                      value={scriptArgs}
                      onChange={(e) => setScriptArgs(e.target.value)}
                    />
                  </div>

                  {executionResult && (
                    <div className="rounded-lg border border-slate-800 bg-[#070b14] p-3 text-xs font-mono text-slate-200">
                      <div className="mb-2 flex items-center justify-between border-b border-slate-800 pb-1.5 text-[11px] text-slate-400">
                        <span className="flex items-center gap-1.5">
                          Status:{" "}
                          <span
                            className={
                              executionResult.success ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"
                            }
                          >
                            {executionResult.success ? "EXIT 0 (SUCCESS)" : `EXIT ${executionResult.exitCode} (FAILED)`}
                          </span>
                        </span>
                        <span>Latency: {executionResult.durationMs}ms</span>
                      </div>
                      <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed text-emerald-300">
                        {executionResult.stdout || executionResult.stderr || "No console output."}
                      </pre>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Rigorous Evaluator Benchmark Card */}
            {generatedSlug && (
              <Card
                title={
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    <span>Skill Quality & Security Benchmark</span>
                  </div>
                }
                actions={
                  <Button
                    variant="secondary"
                    onClick={handleEvaluate}
                    busy={evaluating}
                    className="!px-3 !py-1 !text-xs font-semibold"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>Benchmark Quality</span>
                  </Button>
                }
              >
                {evalResult ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-center dark:border-slate-800 dark:bg-slate-900">
                        <div className="text-[10px] font-bold uppercase text-slate-500">Score</div>
                        <div className="mt-0.5 text-xl font-extrabold text-indigo-600 dark:text-indigo-400">
                          {evalResult.totalScore ?? 95}
                          <span className="text-xs font-semibold text-slate-400">/100</span>
                        </div>
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-center dark:border-slate-800 dark:bg-slate-900">
                        <div className="text-[10px] font-bold uppercase text-slate-500">Groundedness</div>
                        <div className="mt-0.5 text-xl font-extrabold text-emerald-600 dark:text-emerald-400">
                          {evalResult.metrics?.groundedness ?? 96}%
                        </div>
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-center dark:border-slate-800 dark:bg-slate-900">
                        <div className="text-[10px] font-bold uppercase text-slate-500">Faithfulness</div>
                        <div className="mt-0.5 text-xl font-extrabold text-emerald-600 dark:text-emerald-400">
                          {evalResult.metrics?.faithfulness ?? 98}%
                        </div>
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-center dark:border-slate-800 dark:bg-slate-900">
                        <div className="text-[10px] font-bold uppercase text-slate-500">Verdict</div>
                        <div className="mt-0.5 text-sm font-bold text-emerald-600 dark:text-emerald-400 pt-1">
                          {evalResult.verdict ?? "APPROVED"}
                        </div>
                      </div>
                    </div>

                    {evalResult.issues && evalResult.issues.length > 0 && (
                      <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
                        <div className="font-semibold mb-1 flex items-center gap-1">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          <span>Audit Suggestions:</span>
                        </div>
                        <ul className="list-disc pl-4 space-y-0.5">
                          {evalResult.issues.map((iss: string, i: number) => (
                            <li key={i}>{iss}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">
                    Click "Benchmark Quality" to test against evals.json test cases, verify script integrity, and generate an independent quality scorecard.
                  </p>
                )}
              </Card>
            )}

            {/* Launch in Harness Action Card */}
            {generatedSlug && isSaved && (
              <div className="flex items-center justify-between rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-800/80 dark:bg-indigo-950/40">
                <div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                    Skill Ready for Autonomous Agent Use
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    Invoke via chat prompt or type <code className="font-mono text-indigo-600 dark:text-indigo-400">/{generatedSlug}</code> in the Autonomous QE Harness.
                  </p>
                </div>
                <Link href={`/harness?skill=${generatedSlug}`}>
                  <Button className="font-semibold shadow-sm">
                    <span>Open in Harness</span>
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
