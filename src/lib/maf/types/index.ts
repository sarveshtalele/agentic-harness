/**
 * Microsoft Agent Framework (MAF) Core Types & Data Models
 * Aligned with agent-framework.pdf and agentic-qe
 */

export type HarnessMode = "plan" | "execute";

export interface TodoItem {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  createdAt: number;
  completedAt?: number;
  agentId?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, any>;
  result?: any;
  status: "pending" | "running" | "waiting_approval" | "approved" | "rejected" | "completed" | "failed";
  error?: string;
  approvalRequired?: boolean;
  gateNumber?: number;
}

export interface GateApprovalInfo {
  gateNumber: number;
  gateName: string;
  confidenceScore: number;
  confidenceVerdict?: "APPROVED" | "REVISE" | "REJECT";
  artifactSummary: string;
  evidenceCitations?: string[];
  status: "pending" | "approved" | "rejected" | "auto_approved";
  feedback?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  thought?: string;
  agentId?: string;
  toolCalls?: ToolCall[];
  toolCallId?: string;
  createdAt: number;
  gateApproval?: GateApprovalInfo;
}

export interface MagenticSubgoal {
  id: string;
  title: string;
  done: boolean;
  assignedAgent: string;
}

export interface MagenticLedger {
  taskLedger: {
    goal: string;
    subgoals: MagenticSubgoal[];
    constraints: string[];
  };
  progressLedger: {
    completedSteps: string[];
    currentSubgoal: string;
    blockers: string[];
  };
  stallCount: number;
  isStalled: boolean;
}

export interface GateState {
  gateNumber: number;
  name: string;
  status: "not_started" | "pending" | "approved" | "rejected";
  score?: number;
  updatedAt: number;
}

export interface SessionState {
  id: string;
  name: string;
  workingDir: string;
  mode: HarnessMode;
  activeAgentId: string;
  systemPrompt?: string;
  messages: ChatMessage[];
  todos: TodoItem[];
  ledger: MagenticLedger;
  gates: Record<number, GateState>;
  toolsUsed?: Record<string, number>;
  createdAt: number;
  updatedAt: number;
}

export type AGUIEvent =
  | { type: "TEXT_CHUNK"; chunk: string }
  | { type: "THOUGHT_CHUNK"; chunk: string }
  | { type: "AGENT_SWITCH"; agentId: string; agentName: string }
  | { type: "TOOL_CALL_START"; toolCallId: string; toolName: string; args: Record<string, any>; gate?: GateApprovalInfo }
  | { type: "TOOL_CALL_RESULT"; toolCallId: string; result: any; error?: string }
  | { type: "TOOL_APPROVAL_REQUEST"; approvalId: string; toolCallId: string; toolName: string; gate?: GateApprovalInfo; args: Record<string, any> }
  | { type: "STATE_DELTA"; delta: Partial<SessionState> }
  | { type: "ERROR"; code?: string; message: string }
  | { type: "ABORTED" }
  | { type: "RUN_FINISHED"; totalTokens?: number; durationMs?: number };

export interface AIAgentDefinition {
  id: string;
  name: string;
  role: string;
  description: string;
  model: string;
  tools: string[];
  systemPrompt: string;
  color?: string;
  badge?: string;
}

export interface MCPServerConfig {
  id: string;
  name: string;
  transport: "stdio" | "sse";
  command?: string;
  args?: string[];
  sseUrl?: string;
  env?: Record<string, string>;
  status: "connected" | "disconnected" | "error";
  toolsCount?: number;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, any>;
    required?: string[];
  };
  requiresApproval?: boolean;
  gateNumber?: number;
  execute: (args: any, context: ExecutionContext) => Promise<any>;
}

export interface ExecutionContext {
  session: SessionState;
  agentId: string;
  mode: HarnessMode;
  emitEvent: (event: AGUIEvent) => Promise<void>;
  updateSession: (delta: Partial<SessionState>) => Promise<void>;
}
