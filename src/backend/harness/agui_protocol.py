import json
from typing import Dict, Any

class AGUIProtocol:
    """
    MAF AG-UI Protocol Wire Serializer (agent-framework.pdf pp. 510-545)
    Formats events into Server-Sent Events (SSE) data frames for real-time frontend consumption.
    """
    @staticmethod
    def format_sse(event_data: Dict[str, Any]) -> str:
        return f"data: {json.dumps(event_data)}\n\n"

    @staticmethod
    def text_chunk(token: str) -> str:
        return AGUIProtocol.format_sse({"type": "TEXT_CHUNK", "chunk": token})

    @staticmethod
    def thought_chunk(thought: str) -> str:
        return AGUIProtocol.format_sse({"type": "THOUGHT_CHUNK", "chunk": thought})

    @staticmethod
    def agent_switch(agent_id: str, agent_name: str) -> str:
        return AGUIProtocol.format_sse({"type": "AGENT_SWITCH", "agentId": agent_id, "agentName": agent_name})

    @staticmethod
    def tool_call_start(tool_call_id: str, tool_name: str, args: Dict[str, Any], gate: Any = None) -> str:
        return AGUIProtocol.format_sse({
            "type": "TOOL_CALL_START",
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "args": args,
            "gate": gate
        })

    @staticmethod
    def tool_call_result(tool_call_id: str, result: Any, error: str = "") -> str:
        return AGUIProtocol.format_sse({
            "type": "TOOL_CALL_RESULT",
            "toolCallId": tool_call_id,
            "result": result,
            "error": error
        })

    @staticmethod
    def tool_approval_request(approval_id: str, tool_call_id: str, tool_name: str, args: Dict[str, Any], gate: Any = None) -> str:
        return AGUIProtocol.format_sse({
            "type": "TOOL_APPROVAL_REQUEST",
            "approvalId": approval_id,
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "args": args,
            "gate": gate
        })

    @staticmethod
    def state_delta(delta: Dict[str, Any]) -> str:
        return AGUIProtocol.format_sse({"type": "STATE_DELTA", "delta": delta})

    @staticmethod
    def run_finished(duration_ms: int = 0) -> str:
        return AGUIProtocol.format_sse({"type": "RUN_FINISHED", "durationMs": duration_ms})

    @staticmethod
    def aborted(reason: str = "Execution stopped by user") -> str:
        return AGUIProtocol.format_sse({"type": "ABORTED", "reason": reason})
