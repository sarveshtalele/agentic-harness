import { join, dirname, basename, resolve, relative, isAbsolute } from "node:path";
import { existsSync, readFileSync, lstatSync, mkdirSync, writeFileSync, chmodSync, realpathSync } from "node:fs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { userInfo } from "node:os";
import { appendLedger, verifyLedger, ledgerTrust } from "./memory-logger.ts";
import { gateFingerprint, changedSince } from "./fingerprint.ts";

export const GATE_NAMES = ["Intake", "Requirements", "Plan", "Design", "Generate", "Release sign-off"];

/** Project root for a workspace dir (<root>/.qe, or the dir itself for other layouts), same rule as the ledger. */
const rootOfWs = (ws: string): string => (basename(ws) === ".qe" ? dirname(ws) : ws);

export interface Trust { trusted: boolean; reason?: string }

/** A ledger counts only when it verifies and carries this machine's anchor (see memory-logger ledgerTrust). */
export const trustOf = (root: string): Trust => ledgerTrust(root);

export function currentApprover(): string {
  try {
    const name = execFileSync("git", ["config", "user.name"], { encoding: "utf-8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    if (name) return name;
  } catch { /* no git or no user.name */ }
  return userInfo().username;
}

/**
 * Agent-side note of a gate decision. It is logged with source "agent_note",
 * which NEVER counts as approval; only approval-hook (source "user_prompt") can approve a gate.
 */
export function recordGateDecision(
  workspaceDir: string,
  gate: "Gate 0" | "Gate 1" | "Gate 2" | "Gate 3" | "Gate 4" | "Gate 5",
  stage: string,
  decision: "APPROVED" | "REJECTED" | "REVISED",
  notes?: string
): void {
  appendLedger(join(workspaceDir, "ledger.jsonl"), { type: "gate_decision", gate: Number(gate.slice(-1)), stage, decision, notes, approver: currentApprover(), source: "agent_note", timestamp: new Date().toISOString() });
}

export interface GateRecord { decision: "APPROVED" | "REJECTED"; timestamp: string; app?: string }

/** Latest user_prompt decision per gate; empty unless the ledger is trusted and verifies. */
export function userGateRecords(workspaceDir: string): Record<number, GateRecord> {
  const path = join(workspaceDir, "ledger.jsonl");
  const out: Record<number, GateRecord> = {};
  // ponytail: trust (anchor, marker, macs) is defined for <root>/.qe only; other layouts (tests, tools) get chain verification only
  if (!existsSync(path) || (basename(workspaceDir) === ".qe" && !trustOf(rootOfWs(workspaceDir)).trusted) || !verifyLedger(path).ok) return out;
  for (const line of readFileSync(path, "utf-8").split("\n").filter(Boolean)) {
    const r = JSON.parse(line);
    if (r.type === "gate_decision" && r.source === "user_prompt" && (r.decision === "APPROVED" || r.decision === "REJECTED")) out[r.gate] = { decision: r.decision, timestamp: String(r.timestamp ?? ""), ...(r.app ? { app: String(r.app) } : {}) };
  }
  return out;
}

export function userGateDecisions(workspaceDir: string): Record<number, "APPROVED" | "REJECTED"> {
  return Object.fromEntries(Object.entries(userGateRecords(workspaceDir)).map(([g, r]) => [g, r.decision]));
}

export type GateState = "APPROVED" | "REJECTED" | "REOPENED" | "PENDING";

/**
 * Status of gates 0-5 from the trusted ledger. A dashboard doc_edit record reopens its gate and every later APPROVED
 * gate until a later user approval of that gate; approvals still come only from user_prompt records. From 1.5.0 an
 * approval also carries a fingerprint of what it approved: when those files differ now, by any tool, the gate and every
 * later approved gate read as REOPENED (`changed` names the files).
 */
export function gateStatus(workspaceDir: string): Record<number, { status: GateState; timestamp?: string; changed?: string[]; waiver?: { reason: string; gaps: string[] } }> {
  const out: Record<number, { status: GateState; timestamp?: string; changed?: string[]; waiver?: { reason: string; gaps: string[] } }> = Object.fromEntries([0, 1, 2, 3, 4, 5].map((g) => [g, { status: "PENDING" as GateState }]));
  const path = join(workspaceDir, "ledger.jsonl");
  if (!existsSync(path) || (basename(workspaceDir) === ".qe" && !trustOf(rootOfWs(workspaceDir)).trusted) || !verifyLedger(path).ok) return out;
  const prints: Record<number, { app: string; docs: Record<string, string> } | undefined> = {};
  for (const line of readFileSync(path, "utf-8").split("\n").filter(Boolean)) {
    const r = JSON.parse(line);
    const ts = String(r.timestamp ?? "");
    if (r.type === "gate_decision" && r.source === "user_prompt" && (r.decision === "APPROVED" || r.decision === "REJECTED") && out[r.gate]) {
      out[r.gate] = { status: r.decision, timestamp: ts, ...(r.waiver && typeof r.waiver.reason === "string" ? { waiver: { reason: r.waiver.reason, gaps: Array.isArray(r.waiver.gaps) ? r.waiver.gaps.map(String) : [] } } : {}) };
      prints[r.gate] = r.decision === "APPROVED" && r.docs && typeof r.docs === "object" && typeof r.app === "string" ? { app: r.app, docs: r.docs } : undefined;
    } else if (r.type === "doc_edit" && r.source === "dashboard" && Number.isInteger(r.gate)) {
      for (let g = Math.max(0, r.gate); g <= 5; g++) if (out[g].status === "APPROVED") out[g] = { status: "REOPENED", timestamp: ts };
    }
  }
  const root = rootOfWs(workspaceDir);
  for (let g = 0; g <= 5; g++) {
    const p = prints[g];
    if (out[g].status !== "APPROVED" || !p) continue;
    const changed = changedSince(p.docs, gateFingerprint(root, p.app, g));
    if (!changed.length) continue;
    for (let k = g; k <= 5; k++) if (out[k].status === "APPROVED") out[k] = { ...out[k], status: "REOPENED", ...(k === g ? { changed } : {}) };
    break;
  }
  return out;
}

export function isGateApproved(workspaceDir: string, gate: string): boolean {
  try {
    return gateStatus(workspaceDir)[Number(gate.replace(/\D/g, ""))]?.status === "APPROVED";
  } catch {
    return false;
  }
}
