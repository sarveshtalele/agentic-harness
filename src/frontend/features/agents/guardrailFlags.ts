export interface GuardrailFlagDef {
  key: string;
  name: string;
  severity: "critical" | "high" | "medium" | "low";
  action: "REMOVED" | "REDACTED" | "ENFORCED" | "BLOCKED" | "REFUSED" | "AUTO-HEALED" | "THROTTLED";
  summary: string;
  condition: string;
  mitigation: string;
}

export const GUARDRAIL_FLAGS: GuardrailFlagDef[] = [
  {
    key: "prompt_injection",
    name: "Prompt Injection",
    severity: "critical",
    action: "REMOVED",
    summary: "Attempts to hijack the agent system prompt, escape role constraints, or force unvetted outputs.",
    condition: "Input matches known adversarial jailbreak patterns ('Ignore all previous instructions', 'PWNED', role override syntax).",
    mitigation: "Zero-trust token boundary delimiters strip injected instructions before the prompt reaches model context."
  },
  {
    key: "secret",
    name: "Secret Exfiltration",
    severity: "critical",
    action: "REDACTED",
    summary: "Hardcoded credentials, API keys, passwords, or connection strings detected in prompts or outputs.",
    condition: "Entropy scanner or regex detection matches high-entropy strings (e.g. Bearer tokens, AWS/Azure keys, JWTs).",
    mitigation: "Scrubbed with [REDACTED] mask before logging to disk, ledger, or persisting to version history."
  },
  {
    key: "zero_trust",
    name: "Zero-Trust Demarcation",
    severity: "high",
    action: "ENFORCED",
    summary: "Strict sandboxing preventing untrusted repository code from executing within orchestration runtime.",
    condition: "Repository code or test execution invoked during analysis, generation, or verification stages.",
    mitigation: "Subprocess is confined to isolated worktree directory with scrubbed environment variables (clean_env) and non-root execution."
  },
  {
    key: "path_escape",
    name: "Path Traversal / Escape",
    severity: "critical",
    action: "BLOCKED",
    summary: "Attempts to access, write, or unlink files outside the designated project sandbox root.",
    condition: "File path contains directory climbing segments ('..'), symlink escapes, or absolute system paths.",
    mitigation: "safe_path() validates canonical relative resolution within worktree boundary; raises PathEscape if outside."
  },
  {
    key: "tautological_assertion",
    name: "Tautological Assertion",
    severity: "medium",
    action: "REFUSED",
    summary: "Vacuous test assertions that artificially pass without verifying real repository behaviour.",
    condition: "Generated test contains 'assert True', 'expect(true).toBe(true)', or empty test bodies with 'pass'.",
    mitigation: "Static AST checker rejects vacuous asserts and prompts the test-automation-engineer to generate real assertions."
  },
  {
    key: "code_drift",
    name: "AST Symbol Drift / Hallucination",
    severity: "medium",
    action: "AUTO-HEALED",
    summary: "Generated test calls non-existent modules, functions, or hallucinated method signatures.",
    condition: "Static AST analyzer compares test imports and calls against real repository module exports.",
    mitigation: "Sends file back to agent with real ground-truth AST signatures or quarantines failing test cases."
  },
  {
    key: "token_allowance",
    name: "Token Budget Exhaustion",
    severity: "low",
    action: "THROTTLED",
    summary: "Cumulative model token consumption exceeds configured safety limit for the run.",
    condition: "Run token accumulator exceeds ATLAS_RUN_TOKEN_LIMIT threshold.",
    mitigation: "Halts workflow to prevent unexpected API costs; bypassable by Administrator accounts."
  }
];
