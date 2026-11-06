import os
import json
from pydantic import BaseModel
from typing import List, Optional

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "llm_config.json")

class LLMConfig(BaseModel):
    provider: str = "openai"  # openai, deepseek, anthropic, ollama, custom
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.2
    system_prompt: str = (
        "You are the Autonomous Enterprise Agentic QE Harness Assistant. "
        "You operate in accordance with rigorous quality engineering principles: you formulate clear test strategies, "
        "respect Plan vs. Execute mode boundaries, manage Todo tasks using todos_add and todos_complete, "
        "and enforce the Assertion Preservation Rule during test healing. "
        "Provide thorough, professional Quality Engineering analysis and execution."
    )
    available_models: List[str] = [
        "gpt-4o",
        "gpt-4o-mini",
        "deepseek-chat",
        "deepseek-coder",
        "claude-3-7-sonnet",
        "claude-3-5-sonnet",
        "llama3.3",
        "qwen2.5-coder",
    ]

def load_llm_config() -> LLMConfig:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return LLMConfig(**data)
        except Exception as e:
            print(f"[MAF Config] Error reading {CONFIG_FILE}: {e}")
    # Return defaults (with env var fallback if present)
    api_key = os.environ.get("OPENAI_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return LLMConfig(api_key=api_key, base_url=base_url)

def save_llm_config(config: LLMConfig) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2)
    except Exception as e:
        print(f"[MAF Config] Error saving {CONFIG_FILE}: {e}")
