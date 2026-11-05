from typing import Dict, Any
from maf.core.session import SessionState

class QEHandoffExecutor:
    """
    MAF HandoffAgentExecutor Pattern (agent-framework.pdf pp. 280-315)
    Coordinates typed persona transfers between specialized QE agents.
    """
    @staticmethod
    def switch_agent(session: SessionState, target_agent_id: str, reason: str = "") -> Dict[str, Any]:
        prev_agent = session.activeAgentId
        session.activeAgentId = target_agent_id
        return {
            "from": prev_agent,
            "to": target_agent_id,
            "reason": reason
        }
