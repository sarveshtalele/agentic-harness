"""
Enterprise Agentic QE Master HarnessAgent (Modularized Architecture)
Unified loop combining Plan/Execute Mode, Todo tracking, Real LLM streaming,
Human-in-the-Loop Quality Gates, and Tool Execution Guardrails.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple

from .session import SessionState, ChatMessage, ToolCallRecord, GateApprovalInfo, TodoItem
from .mode_provider import AgentModeProvider
from .todo_provider import TodoProvider
from .memory_provider import FileMemoryProvider
from .magentic import MagenticQEOrchestrator
from .approval_manager import global_approval_manager
from .llm_client import LLMClient
from .llm_config import LLMConfig
from .agui_protocol import AGUIProtocol
from .project_repository import global_project_repo
from .cache import global_harness_cache
from backend.harness.qe_agents import get_agent_persona, list_all_agents
from backend.harness.qe_tools import build_qe_tools

# Modularized sub-components
from .intent_classifier import classify_prompt_intent
from .skill_dispatcher import resolve_skill_tool
from .grounding import HarnessGrounding
from .handlers import (
    handle_skill_creation_workflow,
    handle_doc_generation_workflow,
    handle_harness_command,
)
from .handlers.stream_engine import execute_agent_stream


class HarnessAgent:
    """
    Enterprise Agentic QE Master HarnessAgent
    Unified loop combining Plan/Execute Mode, Todo tracking, Real LLM streaming,
    Human-in-the-Loop Quality Gates, and Tool Execution Guardrails.
    """
    def __init__(self, workspace_dir: Optional[str] = None, skill_discovery: Optional[Any] = None):
        self.workspace_dir = workspace_dir or os.getcwd()
        self.mode_provider = AgentModeProvider("plan")
        self.todo_provider = TodoProvider()
        self.memory_provider = FileMemoryProvider(self.workspace_dir)
        self.orchestrator = MagenticQEOrchestrator()
        self.qe_tools = build_qe_tools(self.workspace_dir)
        if skill_discovery:
            self.skill_discovery = skill_discovery
        else:
            from backend.harness.discovery import LocalSkillDiscovery
            self.skill_discovery = LocalSkillDiscovery(self.workspace_dir)

    def _resolve_skill_tool(self, skill_name: str, display_name: str) -> Tuple[str, Dict[str, Any]]:
        """Maps an activated skill identifier to its corresponding executable QE tool."""
        return resolve_skill_tool(skill_name, display_name)

    def _ground_from_centralized_db(self, session: SessionState, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Deterministic grounding against centralized SQLite database (data/atlas.sqlite3)."""
        return HarnessGrounding.ground_from_centralized_db(session, user_prompt)

    async def run(
        self,
        session: SessionState,
        user_prompt: str,
        llm_config: LLMConfig,
        abort_event: Optional[asyncio.Event] = None
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()
        now = int(start_time * 1000)
        prompt_trimmed = user_prompt.strip()
        skill_tool_override = None

        # 1. Semantic Token Cache Check
        cache_key = global_harness_cache.compute_key("prompt_run", {
            "prompt": prompt_trimmed,
            "mode": session.mode,
            "agent": session.activeAgentId,
            "project": session.projectId
        })
        cached_entry = global_harness_cache.get(cache_key)
        if cached_entry and not prompt_trimmed.startswith("/execute") and not prompt_trimmed.startswith("/heal"):
            user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
            asst_msg = ChatMessage(
                id=f"msg_a_{now+1}",
                role="assistant",
                content=cached_entry["content"],
                thought="⚡ Cache Hit: Retrieved from semantic prompt cache (0 tokens consumed).",
                agentId=session.activeAgentId,
                createdAt=now+1
            )
            session.messages.extend([user_msg, asst_msg])
            yield AGUIProtocol.thought_chunk("⚡ Cache Hit: Retrieved from semantic prompt cache (0 tokens consumed).\n")
            yield AGUIProtocol.text_chunk(cached_entry["content"])
            yield AGUIProtocol.format_sse({"type": "CACHE_HIT", "tokensSaved": cached_entry.get("tokens", 350)})
            yield AGUIProtocol.run_finished(15)
            return

        # 2. Centralized Database Grounding (Defects, Documents, Gates, Scans)
        grounded = self._ground_from_centralized_db(session, prompt_trimmed)
        if grounded:
            yield AGUIProtocol.agent_switch("qe-engine", "Autonomous QE Engine")
            yield AGUIProtocol.thought_chunk(grounded["thought"] + "\n")
            
            for tc in grounded["tool_calls"]:
                session.toolsUsed[tc.name] = session.toolsUsed.get(tc.name, 0) + 1
                yield AGUIProtocol.tool_call_start(tc.id, tc.name, tc.args)
                yield AGUIProtocol.tool_call_result(tc.id, tc.result)

            yield AGUIProtocol.text_chunk(grounded["content"])

            user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
            asst_msg = ChatMessage(
                id=f"msg_a_{now+1}",
                role="assistant",
                content=grounded["content"],
                thought=grounded["thought"],
                toolCalls=grounded["tool_calls"],
                agentId="qe-engine",
                createdAt=now+1
            )
            session.messages.extend([user_msg, asst_msg])

            yield AGUIProtocol.state_delta({
                "todos": [t.model_dump() for t in session.todos],
                "gates": {k: v.model_dump() for k, v in session.gates.items()},
                "toolsUsed": session.toolsUsed
            })
            yield AGUIProtocol.run_finished(120)
            return

        # 3. Handle Skill Creator Directives & Commands
        p_lower = prompt_trimmed.lower()
        is_skill_create_cmd = prompt_trimmed.startswith("/") and prompt_trimmed.split(" ")[0].lower() in (
            "/create_agent_skill", "/create-skill", "/scaffold-skill", "/skill-creator"
        )
        is_skill_create_intent = (
            is_skill_create_cmd or
            any(phrase in p_lower for phrase in [
                "create a skill", "build a skill", "scaffold a skill",
                "create skill", "build skill", "scaffold skill",
                "create_agent_skill"
            ])
        )

        if is_skill_create_intent:
            async for chunk in handle_skill_creation_workflow(
                session=session,
                prompt=prompt_trimmed,
                workspace_dir=self.workspace_dir,
                now=now
            ):
                yield chunk
            return

        # 3b. Handle Skill Testing & Live Verification Directives (/test_skill, /run_skill)
        is_skill_test_cmd = prompt_trimmed.startswith("/") and prompt_trimmed.split(" ")[0].lower() in (
            "/test_skill", "/test-skill", "/run_skill", "/run-skill", "/eval_skill", "/evaluate_agent_skill"
        )
        is_skill_test_intent = (
            is_skill_test_cmd or
            any(phrase in p_lower for phrase in [
                "test skill", "run skill", "evaluate skill", "test the skill", "execute skill"
            ])
        )

        if is_skill_test_intent:
            from .skill_tester import handle_skill_testing_workflow
            async for chunk in handle_skill_testing_workflow(
                session=session,
                prompt=prompt_trimmed,
                workspace_dir=self.workspace_dir,
                now=now
            ):
                yield chunk
            return

        # 4. Handle Document Generation Directives & Commands (/doc, /brd, /prd)
        is_doc_cmd = prompt_trimmed.startswith("/") and prompt_trimmed.split(" ")[0].lower() in (
            "/doc", "/docs", "/document", "/brd", "/prd"
        )
        is_doc_intent = (
            is_doc_cmd or
            any(phrase in p_lower for phrase in [
                "create a docuement", "create a document", "create docuement", "create document",
                "generate a document", "generate document", "generate brd", "create brd",
                "brd docuement", "brd document", "prd docuement", "prd document",
                "test plan document", "requirements docuement", "requirements document"
            ])
        )

        if is_doc_intent:
            async for chunk in handle_doc_generation_workflow(
                session=session,
                prompt=prompt_trimmed,
                now=now
            ):
                yield chunk
            return

        # 5. Handle General Slash Commands
        if prompt_trimmed.startswith("/"):
            parts = prompt_trimmed.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/help", "/h", "/?", "/mode", "/m", "/todos", "/tasks", "/todo", "/gates", "/gate", "/skills", "/skill", "/plugin", "/plugins"):
                async for chunk in handle_harness_command(
                    cmd=cmd,
                    arg=arg,
                    prompt_trimmed=prompt_trimmed,
                    session=session,
                    skill_discovery=self.skill_discovery,
                    mode_provider=self.mode_provider,
                    todo_provider=self.todo_provider,
                    now=now
                ):
                    yield chunk
                return

            elif cmd in ("/audit", "/security-audit"):
                skill_tool_override = {"name": "qe_security_audit", "args": {}}
                user_prompt = "Run complete Cloudflare Security Audit on the codebase."
            elif cmd in ("/qe-start", "/discover"):
                skill_tool_override = {"name": "qe_discover_repo", "args": {}}
                user_prompt = "Discover repository structure, detect test frameworks, and initialize test strategy."
            elif cmd in ("/qe-heal", "/heal"):
                skill_tool_override = {"name": "qe_diagnose_and_heal", "args": {"failedTestFile": "tests/test_harness_backend.py", "errorTrace": "Automated harness heal"}}
                user_prompt = "Diagnose test failures and heal drifted selectors while preserving assertions."
            elif cmd in ("/qe-plan", "/plan"):
                session.mode = "plan"
                self.mode_provider.set_mode("plan")
                yield AGUIProtocol.state_delta({"mode": "plan"})
                skill_tool_override = {"name": "qe_plan_strategy", "args": {"scope": arg or "Full Workspace Audit"}}
                user_prompt = f"Plan level-allocated test strategy for: {arg or 'Full Workspace'}"
            elif cmd in ("/qe-execute", "/execute"):
                session.mode = "execute"
                self.mode_provider.set_mode("execute")
                yield AGUIProtocol.state_delta({"mode": "execute"})
                skill_tool_override = {"name": "qe_run_tests", "args": {"command": "npx --no-install vitest run"}}
                user_prompt = f"Execute test generation and running for: {arg or 'Designed test cases'}"
            elif self.skill_discovery.get_skill(cmd.lstrip("/").lower()):
                sk = self.skill_discovery.get_skill(cmd.lstrip("/").lower())
                session.activeAgentId = sk.assignedAgent
                self.todo_provider.todos_add(session, [f"Execute skill: {sk.name} ({sk.displayName})"], agent_id=sk.assignedAgent)
                yield AGUIProtocol.agent_switch(sk.assignedAgent, sk.assignedAgent)
                tool_name, tool_args = self._resolve_skill_tool(sk.name, sk.displayName)

                # Ground skill execution on active project documents and user directive
                doc_context_info = None
                target_prj = session.projectId or "p1"
                try:
                    from backend.db import db
                    with db() as con:
                        latest_doc = con.execute(
                            "SELECT id, title, kind, content FROM documents WHERE project_id=? ORDER BY updated_at DESC LIMIT 1",
                            (target_prj,)
                        ).fetchone()
                        if latest_doc:
                            doc_context_info = {
                                "id": latest_doc[0],
                                "title": latest_doc[1],
                                "kind": latest_doc[2],
                                "content": (latest_doc[3] or "")[:3500]
                            }
                except Exception:
                    pass

                if tool_name == "execute_skill_script":
                    inner_args = tool_args.get("args", {})
                    if not isinstance(inner_args, dict):
                        inner_args = {}
                    if doc_context_info:
                        inner_args["documentId"] = doc_context_info["id"]
                        inner_args["documentTitle"] = doc_context_info["title"]
                        inner_args["documentKind"] = doc_context_info["kind"]
                        inner_args["payload"] = {
                            "documentId": doc_context_info["id"],
                            "documentTitle": doc_context_info["title"],
                            "content": doc_context_info["content"][:2000],
                            "directive": arg or f"Process document '{doc_context_info['title']}' using {sk.name}",
                            "action": "run"
                        }
                    else:
                        inner_args["payload"] = {
                            "directive": arg or f"Execute {sk.name}",
                            "action": "run"
                        }
                    tool_args["args"] = inner_args

                skill_tool_override = {"name": tool_name, "args": tool_args}
                if doc_context_info:
                    user_prompt = (
                        f"Execute skill {sk.name} ({sk.displayName}) taking project document '{doc_context_info['title']}' ({doc_context_info['id']}):\n"
                        f"{sk.description}\n\n"
                        f"Document content:\n{doc_context_info['content'][:1500]}\n\n"
                        f"Directive: {arg or 'Process document according to skill specifications and return structured output'}"
                    )
                else:
                    user_prompt = f"Execute skill {sk.name} ({sk.displayName}): {sk.description}\n\nTask instructions:\n{sk.content[:1000]}"

        # 6. Stream Execution Engine (LLM, Tools, HITL Approvals, State Delta)
        async for chunk in execute_agent_stream(
            session=session,
            user_prompt=user_prompt,
            llm_config=llm_config,
            qe_tools=self.qe_tools,
            mode_provider=self.mode_provider,
            memory_provider=self.memory_provider,
            orchestrator=self.orchestrator,
            todo_provider=self.todo_provider,
            skill_tool_override=skill_tool_override,
            abort_event=abort_event,
            now=now
        ):
            yield chunk
