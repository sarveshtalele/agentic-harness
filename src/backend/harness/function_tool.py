from typing import Callable, Dict, Any, Optional
from pydantic import BaseModel

class FunctionTool:
    """
    MAF FunctionTool abstraction (agent-framework.pdf pp. 210-235)
    """
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
        requires_approval: bool = False,
        gate_number: Optional[int] = None,
        category: str = "Quality Engineering"
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.requires_approval = requires_approval
        self.gate_number = gate_number
        self.category = category

    def to_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    async def execute(self, args: Dict[str, Any], context: Any) -> Any:
        return await self.handler(args, context)
