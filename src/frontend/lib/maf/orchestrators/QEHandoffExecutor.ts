import { AgentSession } from "../core/AgentSession";
import { AGUIEvent } from "../types";

export interface HandoffPayload {
  fromAgentId: string;
  toAgentId: string;
  reason: string;
  contextSummary?: string;
  requiredGate?: number;
}

/**
 * MAF HandoffAgentExecutor Pattern (agent-framework.pdf pp. 280-315)
 * Facilitates typed control handoffs between specialized QE agents.
 */
export class QEHandoffExecutor {
  public static async executeHandoff(
    session: AgentSession,
    payload: HandoffPayload,
    emitEvent: (event: AGUIEvent) => Promise<void>
  ): Promise<void> {
    const prevAgentId = session.getActiveAgentId();
    session.setActiveAgentId(payload.toAgentId);

    // Emit agent switch event to AG-UI protocol
    await emitEvent({
      type: "AGENT_SWITCH",
      agentId: payload.toAgentId,
      agentName: payload.toAgentId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    });

    // Update session state delta
    await emitEvent({
      type: "STATE_DELTA",
      delta: { activeAgentId: payload.toAgentId },
    });

    console.log(`[MAF Handoff] Switched agent: ${prevAgentId} -> ${payload.toAgentId} (Reason: ${payload.reason})`);
  }
}
