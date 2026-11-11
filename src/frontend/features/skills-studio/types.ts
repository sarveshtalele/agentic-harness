export type Kind = "instructions" | "scripts";
export type Assertion = { kind: "contains" | "not_contains" | "regex"; value: string };
export type EvalCase = { input: string; assertions: Assertion[] };
export type Plan = {
  name: string; description: string; tasks: string[];
  files: { path: string; purpose: string }[];
  subagents: { name: string; role: string; when: string }[];
  formats: { name: string; purpose: string; template_path: string }[];
  eval_cases: EvalCase[];
};
export type Check = { check: string; passed: boolean; detail: string };
export type PlanRecord = {
  id: string; project_id: string; kind: Kind; status: "draft" | "approved" | "generated" | string; request: string;
  plan: Plan; source_sha256: string; plan_sha256: string | null; approved_by: string | null; approved_at: string | null;
  prompt_ref: string; checks: Check[];
};
export type Project = { id: string; name: string };
export type Source = { type: "document" | "upload" | "text"; document_id?: string; text?: string; filename?: string };
export type Generated = { files: { path: string; content: string }[]; checks: Check[]; summary: { passed: number; total: number; all_passed: boolean } };
export type Published = { name: string; version: number; sha256: string; checks: Check[] };
