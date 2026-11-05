import { ToolDefinition, GateApprovalInfo } from "../types";

export interface PendingApproval {
  id: string;
  toolCallId: string;
  toolName: string;
  args: Record<string, any>;
  gate?: GateApprovalInfo;
  createdAt: number;
  resolve: (decision: {
    action: "approve" | "reject" | "always_approve";
    feedback?: string;
  }) => void;
}

/**
 * MAF ToolApprovalManager (agent-framework.pdf pp. 210-235)
 * Controls Human-In-The-Loop gate verification and tool execution approvals.
 */
export class ToolApprovalManager {
  private pendingApprovals: Map<string, PendingApproval> = new Map();
  private autoApprovedGates: Set<number> = new Set();
  private autoApprovedTools: Set<string> = new Set();

  /**
   * Checks if a tool call requires human-in-the-loop approval.
   */
  public needsApproval(toolName: string, tool: ToolDefinition, gateNumber?: number): boolean {
    if (gateNumber && this.autoApprovedGates.has(gateNumber)) {
      return false;
    }
    if (this.autoApprovedTools.has(toolName)) {
      return false;
    }
    return Boolean(tool.requiresApproval || gateNumber);
  }

  /**
   * Registers a pending approval and returns a promise that resolves
   * when the user submits an approval or rejection in the UI.
   */
  public registerPending(
    toolCallId: string,
    toolName: string,
    args: Record<string, any>,
    gate?: GateApprovalInfo
  ): { approvalId: string; promise: Promise<{ action: "approve" | "reject" | "always_approve"; feedback?: string }> } {
    const approvalId = `appr_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

    let resolveFn!: (decision: { action: "approve" | "reject" | "always_approve"; feedback?: string }) => void;
    const promise = new Promise<{ action: "approve" | "reject" | "always_approve"; feedback?: string }>((resolve) => {
      resolveFn = resolve;
    });

    this.pendingApprovals.set(approvalId, {
      id: approvalId,
      toolCallId,
      toolName,
      args,
      gate,
      createdAt: Date.now(),
      resolve: resolveFn,
    });

    return { approvalId, promise };
  }

  /**
   * Resolves a pending approval with the user's decision.
   */
  public resolveApproval(
    approvalId: string,
    decision: { action: "approve" | "reject" | "always_approve"; feedback?: string }
  ): boolean {
    const pending = this.pendingApprovals.get(approvalId);
    if (!pending) {
      return false;
    }

    if (decision.action === "always_approve") {
      if (pending.gate?.gateNumber) {
        this.autoApprovedGates.add(pending.gate.gateNumber);
      }
      this.autoApprovedTools.add(pending.toolName);
    }

    pending.resolve(decision);
    this.pendingApprovals.delete(approvalId);
    return true;
  }

  public getPendingList(): Array<Omit<PendingApproval, "resolve">> {
    return Array.from(this.pendingApprovals.values()).map(({ resolve, ...rest }) => rest);
  }
}

// Global singleton instance for cross-request approval resolution
export const globalApprovalManager = new ToolApprovalManager();
