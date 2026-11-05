import { MagenticLedger, MagenticSubgoal, SessionState } from "../types";

/**
 * Magentic-One Style Multi-Agent QE Orchestrator (agent-framework.pdf pp. 320-365)
 * Maintains explicit Task Ledger and Progress Ledger, detects execution stalls,
 * and coordinates specialized QE agents across multi-phase workflows.
 */
export class MagenticQEOrchestrator {
  /**
   * Evaluates the current state and ledger, determining the next agent and subgoal.
   */
  public planNextStep(session: SessionState): {
    nextAgentId: string;
    subgoal: MagenticSubgoal;
    instructions: string;
    isStalled: boolean;
  } {
    const { ledger, mode } = session;
    const subgoals = ledger.taskLedger.subgoals;

    // Check for stall condition
    if (ledger.stallCount >= 3) {
      return {
        nextAgentId: session.activeAgentId,
        subgoal: {
          id: "stall-resolution",
          title: "Execution Stalled: Requesting human guidance",
          done: false,
          assignedAgent: "principal-test-architect",
        },
        instructions: "Execution has stalled after 3 repetitive attempts without state advancement. Pause and request human clarification.",
        isStalled: true,
      };
    }

    // Find first unfinished subgoal
    const currentSubgoal = subgoals.find((sg) => !sg.done) || subgoals[subgoals.length - 1];

    let instructions = "";
    switch (currentSubgoal.id) {
      case "sg-1":
        instructions = "Discover repository structure, detect test frameworks, and map public endpoints.";
        break;
      case "sg-2":
        instructions = "Formulate level-allocated test strategy (Unit, Integration, API, E2E) and rank risk factors.";
        break;
      case "sg-3":
        instructions = "Draft deterministic test case designs with exact input fixtures and expected outputs.";
        break;
      case "sg-4":
        instructions = mode === "plan"
          ? "Harness is in Plan Mode: Summarize planned test code structures and imports without writing files."
          : "Generate 1:1 compilable test automation files in the primary test runner format.";
        break;
      case "sg-5":
        instructions = mode === "plan"
          ? "Harness is in Plan Mode: Outline execution environment and commands."
          : "Execute sandboxed test suites via authorized runner and parse JUnit XML.";
        break;
      case "sg-6":
        instructions = "Analyze failure logs. Heal drifted selectors/fixtures while strictly preserving assertions.";
        break;
      case "sg-7":
        instructions = "Audit test coverage gaps and score confidence (0-100) against repository citations.";
        break;
      default:
        instructions = "Proceed with quality verification.";
    }

    return {
      nextAgentId: currentSubgoal.assignedAgent,
      subgoal: currentSubgoal,
      instructions,
      isStalled: false,
    };
  }

  /**
   * Advances the progress ledger when a subgoal is marked complete.
   */
  public advanceSubgoal(
    ledger: MagenticLedger,
    subgoalId: string,
    completedSummary: string
  ): MagenticLedger {
    const updatedSubgoals = ledger.taskLedger.subgoals.map((sg) =>
      sg.id === subgoalId ? { ...sg, done: true } : sg
    );

    const nextPending = updatedSubgoals.find((sg) => !sg.done);

    return {
      ...ledger,
      taskLedger: {
        ...ledger.taskLedger,
        subgoals: updatedSubgoals,
      },
      progressLedger: {
        completedSteps: [...ledger.progressLedger.completedSteps, completedSummary],
        currentSubgoal: nextPending ? `${nextPending.id}: ${nextPending.title}` : "All subgoals completed",
        blockers: [],
      },
      stallCount: 0,
      isStalled: false,
    };
  }

  /**
   * Records a stalled turn.
   */
  public recordStall(ledger: MagenticLedger, blockerReason: string): MagenticLedger {
    const newStallCount = ledger.stallCount + 1;
    return {
      ...ledger,
      stallCount: newStallCount,
      isStalled: newStallCount >= 3,
      progressLedger: {
        ...ledger.progressLedger,
        blockers: [...ledger.progressLedger.blockers, blockerReason],
      },
    };
  }
}
