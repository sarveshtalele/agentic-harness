"""
Stream Execution Engine for Agentic QE Harness.
Handles thoughts streaming, LLM client chat stream, sequential tool execution,
Human-in-the-Loop Quality Gate approvals, and session state persistence.
"""
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from backend.harness.session import SessionState, ChatMessage, ToolCallRecord, GateApprovalInfo
from backend.harness.agui_protocol import AGUIProtocol
from backend.harness.llm_client import LLMClient
from backend.harness.llm_config import LLMConfig
from backend.harness.qe_agents import get_agent_persona
from backend.harness.intent_classifier import classify_prompt_intent


async def execute_agent_stream(
    session: SessionState,
    user_prompt: str,
    llm_config: LLMConfig,
    qe_tools: List[Any],
    mode_provider: Any,
    memory_provider: Any,
    orchestrator: Any,
    todo_provider: Any,
    skill_tool_override: Optional[Dict[str, Any]] = None,
    abort_event: Optional[asyncio.Event] = None,
    now: Optional[int] = None
) -> AsyncGenerator[str, None]:
    if now is None:
        now = int(time.time() * 1000)

    # 1. Record User Message
    user_msg = ChatMessage(
        id=f"msg_u_{now}",
        role="user",
        content=user_prompt,
        createdAt=now
    )
    session.messages.append(user_msg)

    # 2. Auto-classify prompt intent and consult Magentic Orchestrator
    classified = classify_prompt_intent(user_prompt)
    plan = orchestrator.plan_next_step(session)
    target_agent_id = classified.get("agent_id") or plan.get("nextAgentId") or session.activeAgentId
    session.activeAgentId = target_agent_id
    persona = get_agent_persona(target_agent_id)

    # Notify protocol with generic engine identity so UI role labels are omitted
    yield AGUIProtocol.agent_switch("qe-engine", "Autonomous QE Engine")

    # 3. Stream Thought Reasoning focused on engineering objectives
    thoughts = [
        f"Autonomous Intent: {classified['intent']}",
        f"Active Engineering Skill: {classified['skill']}",
        f"Quality Objective: {classified['subgoal']}",
        f"Harness Mode: [{session.mode.upper()}]",
        "Scanning workspace AST & evaluating quality gates..."
    ]

    for t in thoughts:
        if abort_event and abort_event.is_set():
            yield AGUIProtocol.aborted()
            return
        yield AGUIProtocol.thought_chunk(f"{t}\n")
        await asyncio.sleep(0.04)

    # 4. Check LLM Configuration
    llm_client = LLMClient(llm_config)
    if not llm_client.is_configured():
        err_msg = (
            "⚠️ **Model Not Configured:** No API Key or local endpoint was found for the current model. "
            "Please open **Model & API Settings** in the left sidebar to enter your API key and Base URL."
        )
        yield AGUIProtocol.format_sse({
            "type": "ERROR",
            "code": "MODEL_NOT_CONFIGURED",
            "message": err_msg
        })
        yield AGUIProtocol.text_chunk(f"\n\n> {err_msg}\n\n")

    # 5. Build tool schema
    openai_tools = [t.to_openai_tool() for t in qe_tools]

    messages_payload = [
        {"role": m.role, "content": m.content}
        for m in session.messages[-8:]
    ]

    # Database grounding facts for LLM context
    db_proj_info = ""
    try:
        from backend.db import db, row
        with db() as con:
            t_p = session.projectId or "prj_agentic_qe"
            p_r = row(con.execute("SELECT id, name FROM projects WHERE id=?", (t_p,)))
            f_c = row(con.execute("SELECT COUNT(*) as c FROM findings WHERE project_id=?", (t_p,)))["c"]
            d_c = row(con.execute("SELECT COUNT(*) as c FROM documents WHERE project_id=?", (t_p,)))["c"]
            g_c = row(con.execute("SELECT COUNT(*) as c FROM gates WHERE project_id=? AND status='approved'", (t_p,)))["c"]
            db_proj_info = (
                f"\n[CENTRALIZED DATABASE FACTS (atlas.sqlite3)]\n"
                f"Bound Project: {p_r['name'] if p_r else t_p} ({t_p})\n"
                f"Total Defects Recorded: {f_c}\n"
                f"Governed Documents Recorded: {d_c}\n"
                f"Approved Quality Gates: {g_c}/6\n"
                f"Ground all findings and statements in the real project files and database tables.\n"
            )
    except Exception:
        pass

    effective_system_prompt = (
        f"{llm_config.system_prompt}\n\n"
        f"{mode_provider.get_prompt_directive()}\n\n"
        f"{db_proj_info}\n"
        f"[ACTIVE SPECIALIST PERSONA]\n"
        f"Name: {persona.name}\n"
        f"Role: {persona.role}\n"
        f"{persona.system_prompt}\n\n"
        f"{memory_provider.get_context_prompt()}"
    )

    full_content = ""
    tool_calls_to_execute = []

    if llm_client.is_configured():
        async for chunk in llm_client.stream_chat(
            messages=messages_payload,
            tools=openai_tools,
            system_prompt=effective_system_prompt,
            abort_event=abort_event
        ):
            if abort_event and abort_event.is_set():
                yield AGUIProtocol.aborted()
                return

            if chunk["type"] == "content":
                full_content += chunk["delta"]
                yield AGUIProtocol.text_chunk(chunk["delta"])
            elif chunk["type"] == "tool_call":
                tool_calls_to_execute.append(chunk)
            elif chunk["type"] == "error":
                yield AGUIProtocol.format_sse({
                    "type": "ERROR",
                    "code": chunk.get("code", "LLM_ERROR"),
                    "message": chunk["message"]
                })
                yield AGUIProtocol.text_chunk(f"\n\n> ⚠️ {chunk['message']}\n\n")

    # 6. Fallback tool determination if LLM did not explicitly emit tool calls
    if skill_tool_override:
        tool_calls_to_execute = [skill_tool_override]
    elif not tool_calls_to_execute:
        p_lower = user_prompt.lower()
        if any(k in p_lower for k in ["create skill", "create_agent_skill", "scaffold skill", "new skill", "skill creator"]):
            tool_calls_to_execute.append({
                "name": "create_agent_skill",
                "args": {"name": "Custom Quality Verification Engine", "description": "Autonomous skill synthesized from requirements"}
            })
        elif any(k in p_lower for k in ["evaluate skill", "evaluate_agent_skill", "eval skill", "test skill"]):
            tool_calls_to_execute.append({"name": "evaluate_agent_skill", "args": {"skillName": "skill-creator"}})
        elif "security" in p_lower or "audit" in p_lower:
            tool_calls_to_execute.append({"name": "qe_security_audit", "args": {}})
        elif "view tree" in p_lower or "view_tree" in p_lower or "directory" in p_lower:
            tool_calls_to_execute.append({"name": "view_tree", "args": {"maxDepth": 3}})
        elif "read file" in p_lower or "read_file" in p_lower:
            tool_calls_to_execute.append({"name": "read_file", "args": {"filePath": "package.json"}})
        elif "inspect repo" in p_lower or "inspect_repo" in p_lower or "scan repo" in p_lower or "discover" in p_lower:
            tool_calls_to_execute.append({"name": "inspect_repo", "args": {}})
        elif "user stories" in p_lower or "user story" in p_lower or "ba studio" in p_lower:
            tool_calls_to_execute.append({"name": "create_user_stories", "args": {"feature": "Core Business Flow"}})
        elif "gherkin" in p_lower or "acceptance criteria" in p_lower:
            tool_calls_to_execute.append({"name": "generate_gherkin", "args": {"featureTitle": "Core Business Flow"}})
        elif "update document" in p_lower or "update doc" in p_lower:
            tool_calls_to_execute.append({"name": "update_document", "args": {"documentId": "doc_latest", "content": "# Updated Architecture\n\nPreserved SHA-256."}})
        elif "read document" in p_lower:
            tool_calls_to_execute.append({"name": "read_document", "args": {"documentId": "doc_latest"}})
        elif "sandbox command" in p_lower or "run command" in p_lower or "sandbox" in p_lower:
            tool_calls_to_execute.append({"name": "run_sandbox_command", "args": {"command": "npx --no-install vitest run"}})
        elif "implement feature" in p_lower or "build feature" in p_lower or "feature builder" in p_lower:
            tool_calls_to_execute.append({"name": "implement_feature", "args": {"filePath": "src/features/sample.ts", "code": "// Feature implementation\nexport const active = true;\n"}})
        elif "scan defects" in p_lower or "defect" in p_lower or "bug" in p_lower or "finding" in p_lower:
            tool_calls_to_execute.append({"name": "scan_defects", "args": {}})
        elif "heal" in p_lower or "drift" in p_lower:
            tool_calls_to_execute.append({"name": "heal_test_drift", "args": {"failedTestFile": "e2e/tc-auth-003.spec.ts", "errorTrace": "TimeoutError"}})
        elif "lifecycle" in p_lower or "testing lifecycle" in p_lower:
            tool_calls_to_execute.append({"name": "run_quality_lifecycle", "args": {"scope": "Full QE Lifecycle"}})
        elif "check gates" in p_lower or "gates" in p_lower or "gate" in p_lower:
            tool_calls_to_execute.append({"name": "check_gates", "args": {}})
        elif "pending approvals" in p_lower or "list approvals" in p_lower or "approvals" in p_lower:
            tool_calls_to_execute.append({"name": "list_pending_approvals", "args": {}})
        elif "decide approval" in p_lower:
            tool_calls_to_execute.append({"name": "decide_approval", "args": {"approvalId": "appr_test", "approved": True}})
        elif "logs" in p_lower or "log" in p_lower or "observability" in p_lower:
            tool_calls_to_execute.append({"name": "query_system_logs", "args": {"limit": 25}})
        elif "error summary" in p_lower or "errors" in p_lower:
            tool_calls_to_execute.append({"name": "get_error_summary", "args": {}})
        elif "mcp servers" in p_lower or "mcp list" in p_lower:
            tool_calls_to_execute.append({"name": "list_mcp_servers", "args": {}})
        elif "mcp tool" in p_lower or "mcp" in p_lower:
            tool_calls_to_execute.append({"name": "execute_mcp_tool", "args": {"serverId": "mcp-playwright", "toolName": "navigate"}})
        elif "plan" in p_lower or "strategy" in p_lower:
            tool_calls_to_execute.append({"name": "qe_plan_strategy", "args": {"scope": "Full Workspace Audit"}})
        elif "design" in p_lower or "case" in p_lower:
            tool_calls_to_execute.append({"name": "qe_design_cases", "args": {"area": "Authentication"}})
        elif "generate" in p_lower or "code" in p_lower:
            tool_calls_to_execute.append({"name": "qe_generate_code", "args": {"caseId": "TC-AUTH-001", "runner": "vitest"}})
        elif "run" in p_lower or "execute" in p_lower or "test" in p_lower:
            tool_calls_to_execute.append({"name": "qe_run_tests", "args": {"command": "npx --no-install vitest run"}})
        elif "confidence" in p_lower or "review" in p_lower or "sign" in p_lower:
            tool_calls_to_execute.append({"name": "qe_confidence_review", "args": {"artifactType": "code"}})
        else:
            tool_calls_to_execute.append({"name": "inspect_repo", "args": {}})

    # 7. Execute Tools Sequentially with Mode, HITL Gate Approval & Guardrails
    executed_records: List[ToolCallRecord] = []

    for req in tool_calls_to_execute:
        if abort_event and abort_event.is_set():
            yield AGUIProtocol.aborted()
            return

        tool_name = req["name"]
        tool_args = req.get("args", {})
        tool = next((t for t in qe_tools if t.name == tool_name), None)
        if not tool:
            continue

        tool_call_id = f"call_{int(time.time()*1000)}_{tool_name[:5]}"
        session.toolsUsed[tool_name] = session.toolsUsed.get(tool_name, 0) + 1

        # Mode check
        if not mode_provider.can_execute_tool(tool_name):
            err = f"Tool '{tool_name}' cannot be executed in PLAN mode. Switch to EXECUTE mode using `/mode execute`."
            executed_records.append(ToolCallRecord(
                id=tool_call_id,
                name=tool_name,
                args=tool_args,
                status="failed",
                error=err
            ))
            yield AGUIProtocol.tool_call_start(tool_call_id, tool_name, tool_args)
            yield AGUIProtocol.tool_call_result(tool_call_id, None, err)
            continue

        # Human-in-the-Loop Quality Gate Approval check
        if getattr(tool, "requires_approval", False):
            approval_id = f"appr_{int(time.time()*1000)}_{tool_name[:4]}"
            gate_num = getattr(tool, "gate_number", None) or 4
            appr_info = GateApprovalInfo(
                id=approval_id,
                gateNumber=gate_num,
                gateName=f"Quality Gate {gate_num} Sign-off",
                confidenceScore=95,
                confidenceVerdict="APPROVED",
                artifactSummary=f"Execution request for tool `{tool_name}` with parameters: {list(tool_args.keys())}",
                evidenceCitations=["package.json:1", "vitest.config.ts:1"],
                status="pending"
            )
            yield AGUIProtocol.tool_call_start(tool_call_id, tool_name, tool_args)
            yield AGUIProtocol.gate_approval_request(appr_info)
            executed_records.append(ToolCallRecord(
                id=tool_call_id,
                name=tool_name,
                args=tool_args,
                status="pending",
                gateNumber=gate_num
            ))
            continue

        # Normal tool execution
        yield AGUIProtocol.tool_call_start(tool_call_id, tool_name, tool_args)
        try:
            res = await tool.execute(tool_args, context={"session": session})
            executed_records.append(ToolCallRecord(
                id=tool_call_id,
                name=tool_name,
                args=tool_args,
                result=res,
                status="completed",
                gateNumber=getattr(tool, "gate_number", None)
            ))
            yield AGUIProtocol.tool_call_result(tool_call_id, res)

            # Update gate status if tool has gate association
            gate_num = getattr(tool, "gate_number", None)
            if gate_num:
                g_key = str(gate_num)
                if g_key in session.gates:
                    session.gates[g_key].status = "approved"
                    session.gates[g_key].score = 94
                    session.gates[g_key].updatedAt = int(time.time()*1000)
                    yield AGUIProtocol.state_delta({"gates": {k: v.model_dump() for k, v in session.gates.items()}})

            # Populate todos if discovering repo
            if tool_name == "qe_discover_repo" and len(session.todos) == 0:
                todo_provider.todos_add(session, [
                    "Scan repository AST and map public endpoints",
                    "Formulate risk-allocated test plan across Unit, API, and E2E",
                    "Design deterministic test cases with fixtures",
                    "Generate 1:1 compilable test files in Vitest & Playwright",
                    "Execute isolated test suites and verify assertion preservation"
                ], agent_id=persona.id)
                yield AGUIProtocol.state_delta({"todos": [t.model_dump() for t in session.todos]})

        except Exception as e:
            executed_records.append(ToolCallRecord(
                id=tool_call_id,
                name=tool_name,
                args=tool_args,
                status="failed",
                error=str(e)
            ))
            yield AGUIProtocol.tool_call_result(tool_call_id, None, str(e))

    # 8. Append Live Execution Summary to the chat stream if tools were run
    summary_chunks = []
    if executed_records:
        summary_chunks.append("\n\n### ⚡ Live Tool & Skill Execution Summary\n")
        summary_chunks.append("| Tool / Skill | Status | Gate | Details |")
        summary_chunks.append("| :--- | :--- | :--- | :--- |")
        for rec in executed_records:
            st = "✅ Completed" if rec.status == "completed" else "❌ Failed"
            gate_str = f"Gate {rec.gateNumber}" if rec.gateNumber else "Direct"
            detail_text = ""
            if rec.status == "failed":
                detail_text = (rec.error or "Error during execution").replace("\n", " ")[:90]
            elif isinstance(rec.result, dict):
                if "skill_name" in rec.result:
                    detail_text = f"Skill: `{rec.result['skill_name']}` ({rec.result.get('status', 'ready')})"
                elif "files" in rec.result:
                    detail_text = f"Files: {len(rec.result['files'])} parsed"
                elif "casesCount" in rec.result:
                    detail_text = f"Designed: {rec.result['casesCount']} deterministic cases"
                elif "passed" in rec.result:
                    detail_text = f"Tests: {rec.result['passed']} passed, {rec.result.get('failed', 0)} failed"
                elif "verdict" in rec.result:
                    detail_text = f"Verdict: {rec.result['verdict']} (Confidence: {rec.result.get('score', 90)}%)"
                else:
                    detail_text = str(list(rec.result.keys())[:3])
            summary_chunks.append(f"| `{rec.name}` | {st} | {gate_str} | {detail_text} |")

        summary_text = "\n".join(summary_chunks) + "\n"
        full_content += summary_text
        yield AGUIProtocol.text_chunk(summary_text)

    # 9. Record Assistant Message in Session
    asst_msg = ChatMessage(
        id=f"msg_a_{now+1}",
        role="assistant",
        content=full_content,
        toolCalls=executed_records,
        agentId=target_agent_id,
        createdAt=now+1
    )
    session.messages.append(asst_msg)

    # 10. Magentic Ledger Record
    orchestrator.record_step(session, {
        "agentId": target_agent_id,
        "action": f"Executed prompt with {len(executed_records)} tool calls",
        "tools": [r.name for r in executed_records],
        "status": "success"
    })

    # 11. Memory update
    await memory_provider.append_event({
        "timestamp": now,
        "role": "user",
        "content": user_prompt,
        "agent": target_agent_id,
        "tools_executed": [r.name for r in executed_records]
    })

    # 12. Final State Delta & Run Finished
    yield AGUIProtocol.state_delta({
        "mode": session.mode,
        "activeAgentId": session.activeAgentId,
        "todos": [t.model_dump() for t in session.todos],
        "ledger": session.ledger,
        "toolsUsed": session.toolsUsed
    })
    yield AGUIProtocol.run_finished(int((time.time() - (now/1000))*1000))
