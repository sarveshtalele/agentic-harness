import asyncio
import time
from typing import Dict, Any, Optional

class PendingApproval:
    def __init__(
        self,
        approval_id: str,
        tool_call_id: str,
        tool_name: str,
        args: Dict[str, Any],
        gate: Optional[Dict[str, Any]] = None
    ):
        self.approval_id = approval_id
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.args = args
        self.gate = gate
        self.created_at = int(time.time() * 1000)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        self.future: asyncio.Future = loop.create_future()

class ToolApprovalManager:
    """
    MAF ToolApprovalManager (agent-framework.pdf pp. 210-235)
    Controls Human-In-The-Loop Quality Gate verification and tool execution approvals.
    """
    def __init__(self):
        self.pending_approvals: Dict[str, PendingApproval] = {}
        self.auto_approved_gates: set = set()
        self.auto_approved_tools: set = set()

    def needs_approval(self, tool_name: str, requires_approval: bool, gate_number: Optional[int] = None) -> bool:
        if gate_number and gate_number in self.auto_approved_gates:
            return False
        if tool_name in self.auto_approved_tools:
            return False
        # Only require explicit human-in-the-loop approval if the tool is destructive / marked requires_approval
        return bool(requires_approval)

    def register_pending(
        self,
        tool_call_id: str,
        tool_name: str,
        args: Dict[str, Any],
        gate: Optional[Dict[str, Any]] = None
    ) -> PendingApproval:
        approval_id = f"appr_{int(time.time()*1000)}_{tool_name[:6]}"
        pending = PendingApproval(approval_id, tool_call_id, tool_name, args, gate)
        self.pending_approvals[approval_id] = pending
        return pending

    def resolve_approval(self, approval_id: str, action: str, feedback: Optional[str] = None) -> bool:
        pending = self.pending_approvals.get(approval_id)
        if not pending:
            return False

        if action == "always_approve":
            if pending.gate and pending.gate.get("gateNumber"):
                self.auto_approved_gates.add(pending.gate["gateNumber"])
            self.auto_approved_tools.add(pending.tool_name)

        if not pending.future.done():
            pending.future.set_result({
                "action": action,
                "feedback": feedback or ""
            })

        del self.pending_approvals[approval_id]
        return True

    def get_pending_list(self) -> list:
        return [
            {
                "id": p.approval_id,
                "toolCallId": p.tool_call_id,
                "toolName": p.tool_name,
                "args": p.args,
                "gate": p.gate,
                "createdAt": p.created_at,
            }
            for p in self.pending_approvals.values()
        ]

global_approval_manager = ToolApprovalManager()
