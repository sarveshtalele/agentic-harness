from typing import Dict, Any, List

class CopilotKitProtocol:
    """
    CopilotKit Protocol Adapter for Microsoft Agent Framework
    Translates CopilotKit runtime actions and streaming payloads.
    """
    @staticmethod
    def to_copilotkit_action(tool_definition: Any) -> Dict[str, Any]:
        return {
            "name": tool_definition.name,
            "description": tool_definition.description,
            "parameters": tool_definition.parameters.get("properties", {}),
        }

    @staticmethod
    def format_copilot_response(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "messages": messages,
            "status": "success"
        }
