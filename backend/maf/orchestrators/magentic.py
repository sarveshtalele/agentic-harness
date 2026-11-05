from typing import Dict, Any, Tuple
from maf.core.session import SessionState, MagenticLedger

class MagenticQEOrchestrator:
    """
    Magentic-One Multi-Agent QE Orchestrator (agent-framework.pdf pp. 320-365)
    Coordinates specialized agents with explicit Task Ledger, Progress Ledger,
    and built-in Stall Detector to prevent infinite loops.
    """
    def plan_next_step(self, session: SessionState) -> Dict[str, Any]:
        ledger = session.ledger
        subgoals = ledger.taskLedger.get("subgoals", [])

        # 1. Stall Detection Check
        if ledger.stallCount >= 3:
            return {
                "nextAgentId": session.activeAgentId,
                "subgoal": {
                    "id": "stall-alert",
                    "title": "Execution Stalled: 3 repetitive turns without progress",
                    "assignedAgent": "principal-test-architect"
                },
                "instructions": "Execution has stalled after 3 repetitive attempts without state advancement. Pause and request human clarification.",
                "isStalled": True,
            }

        # 2. Find first incomplete subgoal
        current_subgoal = None
        for sg in subgoals:
            if not sg.get("done", False):
                current_subgoal = sg
                break

        if not current_subgoal and subgoals:
            current_subgoal = subgoals[-1]

        target_agent = current_subgoal.get("assignedAgent", "principal-test-architect") if current_subgoal else "principal-test-architect"

        return {
            "nextAgentId": target_agent,
            "subgoal": current_subgoal,
            "isStalled": False,
        }

    def advance_subgoal(self, session: SessionState, subgoal_id: str, summary: str):
        ledger = session.ledger
        subgoals = ledger.taskLedger.get("subgoals", [])
        for sg in subgoals:
            if sg.get("id") == subgoal_id:
                sg["done"] = True
                break

        # Find next pending
        next_pending = None
        for sg in subgoals:
            if not sg.get("done", False):
                next_pending = sg
                break

        ledger.progressLedger["completedSteps"].append(summary)
        ledger.progressLedger["currentSubgoal"] = (
            f"{next_pending['id']}: {next_pending['title']}" if next_pending else "All subgoals cleared"
        )
        ledger.stallCount = 0
        ledger.isStalled = False
