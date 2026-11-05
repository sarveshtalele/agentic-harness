import json
import httpx
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from .llm_config import LLMConfig

class LLMClient:
    """
    Real asynchronous LLM client compatible with OpenAI, DeepSeek, Ollama, Azure, vLLM,
    and any OpenAI-compatible completions endpoint.
    Hardened against model misconfiguration errors (SEC-04).
    """
    def __init__(self, config: LLMConfig):
        self.config = config

    def is_configured(self) -> bool:
        base_url = self.config.base_url.rstrip("/")
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        return bool(self.config.api_key or is_local)

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        abort_event: Optional[asyncio.Event] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        base_url = self.config.base_url.rstrip("/")
        endpoint = f"{base_url}/chat/completions"

        # Check configuration
        if not self.is_configured():
            yield {
                "type": "error",
                "code": "MODEL_NOT_CONFIGURED",
                "message": (
                    "Model is not configured: No API Key was provided for provider endpoint. "
                    "Open 'Model & API Settings' in the left sidebar to provide your API Key and Base URL."
                )
            }
            return

        prepared_messages = []
        effective_sys = system_prompt or self.config.system_prompt
        if effective_sys:
            # Framing with anti-tamper demarcation (SEC-05)
            framed_sys = f"### [SYSTEM INSTRUCTION BOUNDARY - IMMUTABLE]\n{effective_sys}\n### [END SYSTEM INSTRUCTION]"
            prepared_messages.append({"role": "system", "content": framed_sys})
        prepared_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": prepared_messages,
            "temperature": self.config.temperature,
            "stream": True,
        }

        if tools and len(tools) > 0:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield {
                            "type": "error",
                            "code": f"HTTP_{response.status_code}",
                            "message": f"LLM API Error ({response.status_code}): {err_text.decode('utf-8', errors='ignore')}"
                        }
                        return

                    tool_call_collector: Dict[int, Dict[str, Any]] = {}

                    async for line in response.aiter_lines():
                        if abort_event and abort_event.is_set():
                            yield {"type": "content", "delta": "\n\n⚠️ **Execution stopped by user.**"}
                            return

                        line = line.strip()
                        if not line or line == "data: [DONE]":
                            continue

                        if line.startswith("data: "):
                            raw_json = line[6:]
                            try:
                                chunk = json.loads(raw_json)
                                choice = chunk.get("choices", [{}])[0]
                                delta = choice.get("delta", {})

                                if "content" in delta and delta["content"]:
                                    yield {"type": "content", "delta": delta["content"]}

                                if "tool_calls" in delta:
                                    for tc_delta in delta["tool_calls"]:
                                        index = tc_delta.get("index", 0)
                                        if index not in tool_call_collector:
                                            tool_call_collector[index] = {
                                                "id": tc_delta.get("id", f"call_{index}"),
                                                "name": tc_delta.get("function", {}).get("name", ""),
                                                "args_str": tc_delta.get("function", {}).get("arguments", ""),
                                            }
                                        else:
                                            fn_delta = tc_delta.get("function", {})
                                            if "name" in fn_delta and fn_delta["name"]:
                                                tool_call_collector[index]["name"] += fn_delta["name"]
                                            if "arguments" in fn_delta and fn_delta["arguments"]:
                                                tool_call_collector[index]["args_str"] += fn_delta["arguments"]

                            except json.JSONDecodeError:
                                continue

                    for index, tc_data in tool_call_collector.items():
                        try:
                            parsed_args = json.loads(tc_data["args_str"]) if tc_data["args_str"] else {}
                        except Exception:
                            parsed_args = {"raw": tc_data["args_str"]}
                        yield {
                            "type": "tool_call",
                            "id": tc_data["id"],
                            "name": tc_data["name"],
                            "args": parsed_args
                        }

        except httpx.RequestError as e:
            yield {
                "type": "error",
                "code": "CONNECTION_FAILED",
                "message": f"Failed to connect to LLM endpoint at {endpoint}: {str(e)}"
            }
