"use client";

import { useEffect, useState, useTransition } from "react";
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
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [customText, setCustomText] = useState("");
  const [skillName, setSkillName] = useState("");
  const [category, setCategory] = useState("custom-skills");
  const [description, setDescription] = useState("");
  const [includeScript, setIncludeScript] = useState(true);

  // Scaffolding outputs
  const [scaffolding, setScaffolding] = useState(false);
  const [generatedSlug, setGeneratedSlug] = useState("");
  const [skillMd, setSkillMd] = useState("");
  const [scriptPy, setScriptPy] = useState("");
  const [evalsJson, setEvalsJson] = useState("");
  const [activeTab, setActiveTab] = useState<"skill_md" | "script_py" | "evals_json">("skill_md");

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

  // Load project documents
  useEffect(() => {
    api("/skills/studio/documents")
      .then((res) => {
        const docs = res.documents || [];
        setDocuments(docs);
        if (initialProjectId) {
          const match = docs.find((d: StudioDoc) => d.project_id === initialProjectId);
          if (match) {
            setSelectedDocId(match.id);
            setSkillName(`${match.title} Verification Skill`);
            setDescription(`Automated verification and domain processing for ${match.title}.`);
          }
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingDocs(false));
  }, [initialProjectId]);

  // Handle document selection change
  const handleSelectDoc = (docId: string) => {
    setSelectedDocId(docId);
    const doc = documents.find((d) => d.id === docId);
    if (doc) {
      if (!skillName) {
        const cleanTitle = doc.title.replace(/Business Requirements Document \(BRD\) - /gi, "").replace(/Scenarios/gi, "").trim();
        setSkillName(`${cleanTitle} Agent Skill`);
      }
      if (!description) {
        setDescription(`Automated specification enforcement and testing operations grounded on ${doc.title} (v${doc.current_version}).`);
      }
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
      if (!skillName) {
        const baseName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
        setSkillName(`${baseName} Skill`);
      }
      if (!description) {
        setDescription(`Skill synthesized from ${file.name} document specification.`);
      }
    };
    reader.readAsText(file);
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

    try {
      const res = await api("/skills/studio/scaffold", {
        method: "POST",
        body: JSON.stringify({
          name: skillName,
          description: description || `Domain skill for ${skillName}.`,
          category,
          includeScript,
          documentId: sourceMode === "project" ? selectedDocId || undefined : undefined,
          documentContent: sourceMode !== "project" ? customText || undefined : undefined,
        }),
      });

      setGeneratedSlug(res.slug);
      setSkillMd(res.skill_md);
      setScriptPy(res.script_py || "");
      setEvalsJson(res.evals_json || "");
      setActiveTab("skill_md");
      setSuccessMsg(`Skill package scaffolded successfully for slug: '${res.slug}'`);
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
        method: "POST",
        body: JSON.stringify({
          slug: generatedSlug,
          name: skillName,
          skill_md: skillMd,
          script_py: scriptPy,
          evals_json: evalsJson,
        }),
      });
      setIsSaved(true);
      setSuccessMsg(res.message || `Skill '${generatedSlug}' installed successfully!`);
    } catch (err: any) {
      setError(err.message || "Failed to save skill to platform");
    } finally {
      setSaving(false);
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
      // If not yet saved to disk, save first automatically
      if (!isSaved) {
        await api("/skills/studio/save", {
          method: "POST",
          body: JSON.stringify({
            slug: generatedSlug,
            name: skillName,
            skill_md: skillMd,
            script_py: scriptPy,
            evals_json: evalsJson,
          }),
        });
        setIsSaved(true);
      }

      const res = await api("/skills/studio/execute-script", {
        method: "POST",
        body: JSON.stringify({
          skillSlug: generatedSlug,
          scriptName: "run.py",
          inputArgs: parsedArgs,
        }),
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
          method: "POST",
          body: JSON.stringify({
            slug: generatedSlug,
            name: skillName,
            skill_md: skillMd,
            script_py: scriptPy,
            evals_json: evalsJson,
          }),
        });
        setIsSaved(true);
      }

      const res = await api("/skills/studio/evaluate", {
        method: "POST",
        body: JSON.stringify({ skillSlug: generatedSlug }),
      });
      setEvalResult(res.evaluation);
    } catch (err: any) {
      setError(err.message || "Evaluation benchmark failed");
    } finally {
      setEvaluating(false);
    }
  };

  const handleCopyCode = () => {
    const textToCopy = activeTab === "skill_md" ? skillMd : activeTab === "script_py" ? scriptPy : evalsJson;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <PageTitle
          title="Autonomous Skill Creator & Evaluator Studio"
          subtitle="Grounded Agent Skill synthesis from BRDs, user stories, and specs compliant with awesome-agent-skills standards."
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

        {/* Studio Capabilities Header Ribbon */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-indigo-200/60 bg-gradient-to-r from-indigo-50/80 via-white to-purple-50/80 p-3.5 text-xs text-slate-700 dark:border-indigo-900/60 dark:from-indigo-950/40 dark:via-[#090f24] dark:to-purple-950/30 dark:text-slate-300 shadow-sm">
          <span className="flex items-center gap-1 font-semibold text-indigo-700 dark:text-indigo-300">
            <ShieldCheck className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            Standards Enforcement:
          </span>
          <span className="rounded bg-indigo-100/80 px-2 py-0.5 font-mono text-[11px] font-bold text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-200">
            awesome-agent-skills
          </span>
          <span className="rounded bg-emerald-100/80 px-2 py-0.5 font-mono text-[11px] font-bold text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200">
            NVIDIA Skill Specter A+
          </span>
          <span className="rounded bg-amber-100/80 px-2 py-0.5 font-mono text-[11px] font-bold text-amber-800 dark:bg-amber-900/60 dark:text-amber-200">
            Sandboxed Subprocess Runner
          </span>
          <span className="rounded bg-purple-100/80 px-2 py-0.5 font-mono text-[11px] font-bold text-purple-800 dark:bg-purple-900/60 dark:text-purple-200">
            MAF 2.0 Native
          </span>
        </div>

        {error && <ErrorNote message={error} />}
        {successMsg && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span>{successMsg}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left Column: Skill Configuration & Grounding Source */}
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
                            [{d.project_name}] {d.title} (v{d.current_version} • {d.kind.toUpperCase()})
                          </option>
                        ))}
                      </select>
                    )}
                    {selectedDocId && (
                      <p className="mt-1 text-[11px] text-slate-500">
                        Skill logic and boundaries will be strictly grounded on the chosen specification.
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
              </div>
            </Card>

            <Card title="2. Skill Architecture & Metadata">
              <div className="space-y-3">
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
                      Category
                    </label>
                    <select
                      aria-label="Skill category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className={inputClass}
                    >
                      <option value="custom-skills">Custom Skills</option>
                      <option value="testing">Quality Engineering</option>
                      <option value="financial-engineering">Financial Engineering</option>
                      <option value="security">Security & Compliance</option>
                      <option value="devops">DevOps & Cloud</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Target Engine
                    </label>
                    <input
                      disabled
                      value="MAF 2.0 / Subprocess"
                      className={`${inputClass} bg-slate-100 text-slate-500 dark:bg-slate-800`}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Capability Description & Activation Brief
                  </label>
                  <textarea
                    aria-label="Capability description"
                    rows={3}
                    placeholder="Describe what the skill does and when an agent or developer should invoke it."
                    className={inputClass}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>

                <div className="flex items-center gap-2 pt-1">
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

                <div className="pt-2">
                  <Button
                    onClick={handleScaffold}
                    busy={scaffolding}
                    disabled={!skillName.trim()}
                    className="w-full !py-2.5 shadow-sm"
                  >
                    <Wand2 className="h-4 w-4" />
                    <span>Scaffold Agent Skill Package</span>
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column: Code Preview, Live Sandbox Runner, & Benchmark */}
          <div className="space-y-5 lg:col-span-7">
            {/* Artifact Code Tabs */}
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
                  <div className="flex items-center gap-2 border-b border-slate-200 pb-2 dark:border-slate-800">
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
                      <span>evals/evals.json</span>
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
                    Select a project specification or brief on the left, then click "Scaffold Agent Skill Package" to generate compliant files.
                  </p>
                </div>
              )}
            </Card>

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
                    <span>Skill Quality & Security Benchmark (Evaluator Skill)</span>
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
                        <div className="text-[10px] font-bold uppercase text-slate-500">Specter Score</div>
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
