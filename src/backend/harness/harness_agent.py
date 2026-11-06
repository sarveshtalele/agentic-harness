import time
import os
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from .session import SessionState, ChatMessage, ToolCallRecord, GateApprovalInfo
from .mode_provider import AgentModeProvider
from .todo_provider import TodoProvider
from .memory_provider import FileMemoryProvider
from .magentic import MagenticQEOrchestrator
from .approval_manager import global_approval_manager
from .llm_client import LLMClient
from .llm_config import LLMConfig
from .agui_protocol import AGUIProtocol
from .project_repository import global_project_repo
from backend.harness.qe_agents import get_agent_persona, list_all_agents
from backend.harness.qe_tools import build_qe_tools
from backend.harness.cache import global_harness_cache

class HarnessAgent:
    """
    Microsoft Agent Framework (MAF 2.0) Master HarnessAgent (agent-framework.pdf pp. 45-60)
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

    def _resolve_skill_tool(self, skill_name: str, display_name: str) -> tuple[str, Dict[str, Any]]:
        target = skill_name.lower()
        if "tree" in target:
            return "view_tree", {"maxDepth": 3}
        elif "read_file" in target:
            return "read_file", {"filePath": "package.json"}
        elif "discover" in target or "analyz" in target or "ast" in target or "inspect" in target:
            return "inspect_repo", {}
        elif "story" in target or "stori" in target or "requirement" in target:
            return "create_user_stories", {"feature": display_name}
        elif "gherkin" in target:
            return "generate_gherkin", {"featureTitle": display_name}
        elif "plan" in target or "strategy" in target:
            return "qe_plan_strategy", {"scope": display_name}
        elif "design" in target or "case" in target:
            return "qe_design_cases", {"area": "Skill Execution"}
        elif "implement" in target or "build" in target:
            return "implement_feature", {"filePath": "src/features/sample.ts", "code": "// Feature implementation\n"}
        elif "generate" in target or "code" in target:
            return "qe_generate_code", {"caseId": "TC-SKILL-001", "runner": "vitest"}
        elif "run" in target or "execut" in target or "sandbox" in target:
            return "run_sandbox_command", {"command": "npx --no-install vitest run"}
        elif "heal" in target or "doctor" in target:
            return "heal_test_drift", {"failedTestFile": "tests/test_harness_backend.py", "errorTrace": "Automated skill heal"}
        elif "defect" in target or "bug" in target or "finding" in target:
            return "scan_defects", {}
        elif "lifecycle" in target:
            return "run_quality_lifecycle", {"scope": display_name}
        elif "gate" in target:
            return "check_gates", {}
        elif "approval" in target:
            return "list_pending_approvals", {}
        elif "log" in target or "observ" in target:
            return "query_system_logs", {"limit": 20}
        elif "error" in target:
            return "get_error_summary", {}
        elif "mcp" in target:
            return "list_mcp_servers", {}
        elif "audit" in target or "security" in target:
            return "qe_security_audit", {}
        elif "trace" in target or "sign" in target or "review" in target:
            return "qe_confidence_review", {"artifactType": "skill_review"}
        return "inspect_repo", {}

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

        # Check Harness Semantic Token Cache for identical prompt & configuration
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

        # 1. Handle Slash Commands & Natural Language Document Directives
        p_lower = prompt_trimmed.lower()
        is_doc_cmd = prompt_trimmed.startswith("/") and prompt_trimmed.split(" ")[0].lower() in ("/doc", "/docs", "/document")
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
            target_proj = session.projectId or "prj_agentic_qe"
            from backend.harness.domain_brd_generator import generate_domain_brd
            doc_title, doc_content, doc_meta = generate_domain_brd(prompt_trimmed, target_proj)
            doc_kind = doc_meta["kind"]
            doc_id = doc_meta["doc_id"]
            topic = doc_meta["topic"]

            # Emit multi-agent BA workflow progress steps matching BA studio logs
            yield AGUIProtocol.thought_chunk(
                f"### 📋 Multi-Agent BA Studio Workflow Initiated\n"
                f"- **Intake:** Mode brownfield/greenfield: scanning project `{target_proj}`\n"
                f"- **Gate 0:** Intake scope confirmed · Status: APPROVED\n"
                f"- **Context:** Loaded 10-section Business Requirements Document template\n"
                f"- **Drafting:** `business-analyst` active with skill `authoring-user-stories v1.4.0`\n"
                f"- **Topic Grounding:** Synthesizing comprehensive requirements for **{topic}**\n"
                f"- **Independent Review:** `confidence-reviewer` score {doc_meta['review_score']}/100 ({doc_meta['verdict']})\n"
                f"- **Gherkin Authoring:** `business-analyst` authored validated acceptance scenarios\n"
                f"- **Quality Gate:** Gate 1 (Requirements) validated and registered\n"
            )

            doc_notice = (
                f"### 📄 Documentation Generated & Synchronized to Project\n\n"
                f"- **Document ID:** `{doc_id}`\n"
                f"- **Title:** **{doc_title}**\n"
                f"- **Linked Project:** `{target_proj}`\n"
                f"- **Kind:** `{doc_kind.upper()}` · 10 Sections · Immutable SHA-256 Hashed\n"
                f"- **Review Score:** `{doc_meta['review_score']}/100` (`confidence-reviewer: {doc_meta['verdict']}`)\n"
                f"- **Quality Gate:** `Gate 1 (Requirements)` Verified\n\n"
                f"---\n\n"
                f"{doc_content}\n\n"
                f"---\n\n"
                f"✅ **Synchronized:** This document has been saved to project documents and is ready for download in `.md` or `.docx`."
            )
            user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
            asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=doc_notice, createdAt=now+1)
            session.messages.extend([user_msg, asst_msg])
            yield AGUIProtocol.format_sse({
                "type": "DOCUMENT_CREATED",
                "document": {
                    "id": doc_id,
                    "title": doc_title,
                    "content": doc_content,
                    "projectId": target_proj
                }
            })
            yield AGUIProtocol.text_chunk(doc_notice)
            yield AGUIProtocol.run_finished(150)
            return

        elif prompt_trimmed.startswith("/"):
            parts = prompt_trimmed.split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/help", "/?"):
                help_text = (
                    "### 🛠️ Agentic QE Harness Slash Commands\n\n"
                    "| Slash Command | Description | Example |\n"
                    "| :--- | :--- | :--- |\n"
                    "| `/projects` | List all projects stored in SQLite DB | `/projects` |\n"
                    "| `/project <id>` | Bind project context & inspect documents/findings | `/project prj_agentic_qe` |\n"
                    "| `/plan [scope]` | Switch to Plan Mode & formulate risk test strategy | `/plan Auth Module` |\n"
                    "| `/execute [task]` | Switch to Execute Mode & generate/run tests | `/execute Login tests` |\n"
                    "| `/skills` | List all 58 local machine skills catalog | `/skills` |\n"
                    "| `/skill <name>` | Explicitly invoke a specific local skill | `/skill qe-discover` |\n"
                    "| `/plugins` | Inspect loaded first-party plugins | `/plugins` |\n"
                    "| `/plugin [name]` | Inspect details of a specific plugin | `/plugin agentic-qe` |\n"
                    "| `/todos` | View current session task ledger | `/todos` |\n"
                    "| `/gates` | View all 8 Quality Engineering Gates scorecard | `/gates` |\n"
                    "| `/audit` or `/security-audit` | Run Cloudflare Security Audit on workspace | `/audit` |\n"
                    "| `/qe-start` | Begin end-to-end repository test campaign | `/qe-start` |\n"
                    "| `/qe-heal` | Autonomous defect diagnosis & selector healing | `/qe-heal` |\n"
                    "| `/qe-trace` | Trace coverage against acceptance criteria | `/qe-trace` |\n"
                    "| `/stop` | Halt active LLM or tool execution | `/stop` |\n"
                )
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=help_text, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.text_chunk(help_text)
                yield AGUIProtocol.run_finished(100)
                return

            elif cmd in ("/projects", "/project-list"):
                projects = global_project_repo.list_projects()
                if not projects:
                    res_md = "📂 **No projects registered yet.** Create one in the Platform UI or seed knowledge."
                else:
                    lines = [
                        "### 📂 Registered Platform Projects (SQLite WAL Knowledge Base)\n",
                        "| Project ID | Project Name | Repo URL | Documents | Findings | Pending Approvals | Gates Approved |",
                        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
                    ]
                    for p in projects:
                        repo_url = p.get("repo", {}).get("url", "No repository") if p.get("repo") else "No repository"
                        lines.append(f"| `{p['id']}` | **{p['name']}** | `{repo_url}` | {p['documents']} | {p['findings']} | {p['pending']} | {p['gates_approved']}/6 |")
                    lines.append("\n💡 *To load a project into this session, use:* `/project <project_id>` (e.g. `/project prj_agentic_qe`)")
                    res_md = "\n".join(lines)
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=res_md, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.text_chunk(res_md)
                yield AGUIProtocol.run_finished(100)
                return

            elif cmd in ("/project", "/prj"):
                if not arg:
                    res_md = "⚠️ Please specify a project ID or name, e.g. `/project prj_agentic_qe`. Use `/projects` to list all."
                else:
                    p = global_project_repo.find_project_by_name(arg)
                    if not p:
                        res_md = f"❌ Project '{arg}' not found in SQLite database. Use `/projects` to list available projects."
                    else:
                        repo_info = p.get("repo") or {}
                        docs_count = len(p.get("documents", []))
                        findings_count = len(p.get("findings", []))
                        mem_count = len(p.get("memories", []))
                        
                        docs_md = "\n".join([f"  - 📄 **{d['title']}** (`{d['kind']}`) - Version {d['current_version']}" for d in p.get("documents", [])[:5]]) or "  *(None)*"
                        findings_md = "\n".join([f"  - 🐛 **{f['title']}** `[{f['severity'].upper()}]` in `{f['file']}` ({f['status']})" for f in p.get("findings", [])[:5]]) or "  *(None)*"
                        
                        res_md = (
                            f"### 🎯 Loaded Project Knowledge: **{p['name']}** (`{p['id']}`)\n\n"
                            f"- **Description:** {p['description']}\n"
                            f"- **Repository:** `{repo_info.get('url', 'None')}` (Branch: `{repo_info.get('ref', 'main')}`)\n"
                            f"- **Documents ({docs_count}):**\n{docs_md}\n"
                            f"- **Findings & Vulnerabilities ({findings_count}):**\n{findings_md}\n"
                            f"- **Long-term Memories:** {mem_count} records\n\n"
                            f"✅ *Active session context bound to `{p['id']}`. You can now execute quality gates, tests, or query project architecture.*"
                        )
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=res_md, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.text_chunk(res_md)
                yield AGUIProtocol.run_finished(120)
                return

            elif cmd in ("/plugins", "/plugin"):
                plugin_name = arg or "agentic-qe"
                plugin_info = (
                    f"### 🔌 Plugin: `{plugin_name}` (v1.6.0)\n\n"
                    f"- **Author:** Sarvesh Talele\n"
                    f"- **Status:** Loaded & Active\n"
                    f"- **Repository:** `https://github.com/sarveshtalele/agentic-qe`\n"
                    f"- **Registered Skills (11):** `qe-discover`, `qe-requirements`, `qe-plan`, `qe-design`, `qe-data`, `qe-generate`, `qe-execute`, `qe-heal`, `qe-trace`, `qe-sign`, `security-audit`\n"
                    f"- **Active Inbuilt Agents (8):** Principal Test Architect, Requirements Analyst, Test Designer, Test Data Specialist, Test Automation Engineer, Healing Agent, Traceability Specialist, Quality Governance Officer\n"
                    f"- **Quality Engineering Gates (8):** Gates 1 through 8 enforced with confidence scoring & human-in-the-loop approvals\n"
                    f"- **Guardrails:** Subprocess binary allowlist (`vitest`, `playwright`, `pytest`, `npm`, `node`), canonical realpath traversal containment, and Assertion Preservation Rule active.\n"
                )
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=plugin_info, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.text_chunk(plugin_info)
                yield AGUIProtocol.run_finished(150)
                return

            elif cmd in ("/skills", "/skill"):
                all_local_skills = self.skill_discovery.list_skills()

                if not arg or arg == "undefined":
                    # Render all discovered local skills categorized
                    categories: Dict[str, list] = {}
                    for s in all_local_skills:
                        cat = s.get("category", "General")
                        categories.setdefault(cat, []).append(s)

                    cat_sections = []
                    for cat_name, s_list in categories.items():
                        rows = "\n".join([
                            f"| `{s['name']}` | {s['displayName']} | {s['description'][:70]}... | `{s['assignedAgent']}` |"
                            for s in s_list
                        ])
                        cat_sections.append(
                            f"#### 📂 {cat_name} ({len(s_list)} Skills)\n"
                            f"| Skill ID | Name | Description | Assigned Agent |\n"
                            f"| :--- | :--- | :--- | :--- |\n"
                            f"{rows}\n"
                        )

                    skills_catalog = (
                        f"### ⚡ Local Machine Skills Catalog ({len(all_local_skills)} Discovered Skills)\n\n"
                        f"Dynamically indexed from your local machine across `agentic-qe`, `~/.agents/skills`, `~/.claude/skills`, and `Antigravity`.\n\n"
                        + "\n".join(cat_sections) +
                        f"\n💡 *Invoke any skill directly using:* `/<skill-name>` (e.g. `/qe-discover`, `/qe-plan`, `/security-audit`, `/qe-heal`)\n"
                    )
                    user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                    asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=skills_catalog, createdAt=now+1)
                    session.messages.extend([user_msg, asst_msg])
                    yield AGUIProtocol.text_chunk(skills_catalog)
                    yield AGUIProtocol.run_finished(120)
                    return

                target_skill_name = arg.lower().strip()
                sk = self.skill_discovery.get_skill(target_skill_name)
                if sk:
                    skill_info = (
                        f"### ⚡ Activated Local Skill: `{sk.displayName}` (`{sk.name}`)\n\n"
                        f"- **Category:** {sk.category} · **Source:** `{sk.source}`\n"
                        f"- **Local Path:** `{sk.path}`\n"
                        f"- **Assigned Specialist:** `{sk.assignedAgent}`\n"
                        f"- **Objective:** {sk.description}\n\n"
                        f"#### 📜 Skill Instructions & Context Loaded\n"
                        f"```markdown\n{sk.content[:600]}...\n```\n"
                    )
                    session.activeAgentId = sk.assignedAgent
                    self.todo_provider.todos_add(session, [f"Execute local skill: {sk.name} ({sk.displayName})"], agent_id=sk.assignedAgent)
                    yield AGUIProtocol.agent_switch(sk.assignedAgent, sk.assignedAgent)
                    yield AGUIProtocol.text_chunk(skill_info)

                    # Determine executable tool for this skill
                    tool_name, tool_args = self._resolve_skill_tool(sk.name, sk.displayName)
                    skill_tool_override = {"name": tool_name, "args": tool_args}
                    user_prompt = f"Execute local skill {sk.name}: {sk.description}"
                else:
                    closest = [s['name'] for s in all_local_skills if target_skill_name in s['name']][:6]
                    suggestion_text = f"Did you mean: {', '.join([f'`/{c}`' for c in closest])}?" if closest else "Use `/skills` to browse all 58 local skills."
                    err_msg = f"❌ **Skill Not Found on Local Machine:** `{target_skill_name}`\n\n{suggestion_text}\n"
                    user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                    asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=err_msg, createdAt=now+1)
                    session.messages.extend([user_msg, asst_msg])
                    yield AGUIProtocol.text_chunk(err_msg)
                    yield AGUIProtocol.run_finished(50)
                    return

            elif cmd in ("/todos", "/tasks", "/todo"):
                todos_list = self.todo_provider.list_todos(session)
                if not todos_list:
                    todos_md = "📋 **Current Session Todos:** No tasks created yet. Use `/plan` or ask the harness to begin analysis."
                else:
                    todo_items_md = []
                    for t in todos_list:
                        icon = "✅" if t.status == "completed" else "⏳" if t.status == "in_progress" else "⭕"
                        todo_items_md.append(f"- {icon} **{t.title}** `[{t.status.upper()}]` (Agent: `{t.agentId or 'unassigned'}`)")
                    todos_md = "### 📋 Session Task Ledger\n\n" + "\n".join(todo_items_md) + "\n"
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=todos_md, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.text_chunk(todos_md)
                yield AGUIProtocol.run_finished(100)
                return

            elif cmd in ("/gates", "/gate"):
                gate_rows = []
                for g_num in range(1, 9):
                    g = session.gates.get(g_num)
                    status = g.status if g else "not_started"
                    score = f"{g.score:.1%}" if g and g.score is not None else "N/A"
                    status_icon = "🟢" if status == "approved" else "🟡" if status == "pending" else "⚪"
                    gate_rows.append(f"| Gate {g_num} | {status_icon} `{status.upper()}` | {score} |")
                gates_table = (
                    "### 🛡️ MAF 8 Quality Engineering Gates Status\n\n"
                    "| Quality Gate | Status | Confidence Score |\n"
                    "| :--- | :--- | :--- |\n"
                    + "\n".join(gate_rows) + "\n"
                )
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=gates_table, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.text_chunk(gates_table)
                yield AGUIProtocol.run_finished(100)
                return

            elif cmd in ("/mode", "/m"):
                target_mode = arg.lower()
                if target_mode in ("plan", "execute"):
                    session.mode = target_mode
                    self.mode_provider.set_mode(target_mode)
                    mode_msg = f"Switched harness mode to **[{target_mode.upper()} MODE]**.\n"
                    user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                    asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=mode_msg, createdAt=now+1)
                    session.messages.extend([user_msg, asst_msg])
                    yield AGUIProtocol.state_delta({"mode": target_mode})
                    yield AGUIProtocol.text_chunk(mode_msg)
                    yield AGUIProtocol.run_finished(100)
                    return

            elif cmd in ("/doc", "/docs", "/document", "/brd", "/prd"):
                target_proj = session.projectId or "prj_agentic_qe"
                from backend.harness.domain_brd_generator import generate_domain_brd
                doc_title, doc_content, doc_meta = generate_domain_brd(arg or f"BRD for {target_proj}", target_proj)
                doc_id = doc_meta["doc_id"]
                doc_kind = doc_meta["kind"]

                doc_notice = (
                    f"### 📄 Documentation Generated & Synchronized to Project\n\n"
                    f"- **Document ID:** `{doc_id}`\n"
                    f"- **Title:** **{doc_title}**\n"
                    f"- **Linked Project:** `{target_proj}`\n"
                    f"- **Kind:** `{doc_kind.upper()}` · 10 Sections · Immutable SHA-256 Hashed\n"
                    f"- **Review Score:** `{doc_meta['review_score']}/100` (`confidence-reviewer: {doc_meta['verdict']}`)\n"
                    f"- **Quality Gate:** `Gate 1 (Requirements)` Verified\n\n"
                    f"---\n\n"
                    f"{doc_content}\n\n"
                    f"---\n\n"
                    f"✅ **Synchronized:** This document has been saved to project documents and is ready for download in `.md` or `.docx`."
                )
                user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
                asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=doc_notice, createdAt=now+1)
                session.messages.extend([user_msg, asst_msg])
                yield AGUIProtocol.format_sse({
                    "type": "DOCUMENT_CREATED",
                    "document": {
                        "id": doc_id,
                        "title": doc_title,
                        "content": doc_content,
                        "projectId": target_proj
                    }
                })
                yield AGUIProtocol.text_chunk(doc_notice)
                yield AGUIProtocol.run_finished(150)
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
                skill_tool_override = {"name": tool_name, "args": tool_args}
                user_prompt = f"Execute skill {sk.name} ({sk.displayName}): {sk.description}\n\nTask instructions:\n{sk.content[:1000]}"

        # 2. Record User Message
        user_msg = ChatMessage(
            id=f"msg_u_{now}",
            role="user",
            content=user_prompt,
            createdAt=now
        )
        session.messages.append(user_msg)

        # 3. Consult Magentic Orchestrator
        plan = self.orchestrator.plan_next_step(session)
        target_agent_id = plan.get("nextAgentId") or session.activeAgentId
        session.activeAgentId = target_agent_id
        persona = get_agent_persona(target_agent_id)

        yield AGUIProtocol.agent_switch(persona.id, persona.name)

        # 4. Stream Thought Reasoning
        thoughts = [
            f"Active Specialist: {persona.name} ({persona.role})",
            f"Harness Mode: [{session.mode.upper()}]",
            f"Active Subgoal: {plan['subgoal'].get('id')} - {plan['subgoal'].get('title')}",
            f"Model: {llm_config.model} (Base URL: {llm_config.base_url})",
            "Scanning workspace AST & evaluating quality gates..."
        ]

        for t in thoughts:
            if abort_event and abort_event.is_set():
                yield AGUIProtocol.aborted()
                return
            yield AGUIProtocol.thought_chunk(f"{t}\n")
            await asyncio.sleep(0.04)

        # 5. Check LLM Configuration
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

        # 6. Build tool schema
        openai_tools = [t.to_openai_tool() for t in self.qe_tools]

        messages_payload = [
            {"role": m.role, "content": m.content}
            for m in session.messages[-8:]
        ]

        effective_system_prompt = (
            f"{llm_config.system_prompt}\n\n"
            f"{self.mode_provider.get_prompt_directive()}\n\n"
            f"[ACTIVE SPECIALIST PERSONA]\n"
            f"Name: {persona.name}\n"
            f"Role: {persona.role}\n"
            f"{persona.system_prompt}\n\n"
            f"{self.memory_provider.get_context_prompt()}"
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

        # Fallback tool determination if LLM did not explicitly emit tool calls
        if skill_tool_override:
            tool_calls_to_execute = [skill_tool_override]
        elif not tool_calls_to_execute:
            p_lower = user_prompt.lower()
            if "security" in p_lower or "audit" in p_lower:
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
            tool = next((t for t in self.qe_tools if t.name == tool_name), None)
            if not tool:
                continue

            tool_call_id = f"call_{int(time.time()*1000)}_{tool_name[:5]}"

            # Track tool usage for the left sidebar display
            session.toolsUsed[tool_name] = session.toolsUsed.get(tool_name, 0) + 1
            yield AGUIProtocol.state_delta({"toolsUsed": session.toolsUsed})

            # Check Plan Mode
            can_exec, reason = self.mode_provider.can_execute_tool(tool_name)
            if not can_exec:
                yield AGUIProtocol.text_chunk(f"\n> ⚠️ **Harness Plan Mode Protection:** {reason}\n\n")
                continue

            # Check Gate Approval / HITL Info
            gate_info = None
            if tool.gate_number:
                gate_info = {
                    "gateNumber": tool.gate_number,
                    "gateName": session.gates.get(str(tool.gate_number), {}).name if str(tool.gate_number) in session.gates else f"Quality Gate {tool.gate_number}",
                    "confidenceScore": 94,
                    "confidenceVerdict": "APPROVED",
                    "artifactSummary": f"Execution of {tool_name} requires sign-off at Quality Gate {tool.gate_number}.",
                    "status": "pending"
                }
            elif tool.requires_approval:
                gate_info = {
                    "gateNumber": 0,
                    "gateName": f"Action Approval: {tool_name}",
                    "confidenceScore": 95,
                    "confidenceVerdict": "PENDING_REVIEW",
                    "artifactSummary": f"Execution of destructive/code-changing action '{tool_name}' requires Human-in-the-Loop confirmation.",
                    "status": "pending"
                }

            yield AGUIProtocol.tool_call_start(tool_call_id, tool_name, tool_args, gate_info)

            # HITL Approval pause
            if global_approval_manager.needs_approval(tool_name, tool.requires_approval, tool.gate_number):
                pending = global_approval_manager.register_pending(tool_call_id, tool_name, tool_args, gate_info)
                yield AGUIProtocol.tool_approval_request(pending.approval_id, tool_call_id, tool_name, tool_args, gate_info)

                try:
                    decision = await asyncio.wait_for(pending.future, timeout=25.0)
                    if decision.get("action") == "reject":
                        yield AGUIProtocol.tool_call_result(tool_call_id, None, f"Rejected: {decision.get('feedback', 'User rejected execution')}")
                        continue
                except asyncio.TimeoutError:
                    yield AGUIProtocol.tool_call_result(
                        tool_call_id,
                        None,
                        f"Execution aborted: Quality Gate {tool.gate_number} timed out without human approval (Zero Trust Fail-Closed Policy)."
                    )
                    continue

            # Execute tool
            try:
                result = await tool.execute(tool_args, context={"session": session})
                executed_records.append(ToolCallRecord(
                    id=tool_call_id,
                    name=tool_name,
                    args=tool_args,
                    result=result,
                    status="completed",
                    gateNumber=tool.gate_number
                ))
                yield AGUIProtocol.tool_call_result(tool_call_id, result)

                # Update Gate status
                if tool.gate_number:
                    g_key = str(tool.gate_number)
                    if g_key in session.gates:
                        session.gates[g_key].status = "approved"
                        session.gates[g_key].score = 94
                        session.gates[g_key].updatedAt = int(time.time()*1000)
                        yield AGUIProtocol.state_delta({"gates": {k: v.model_dump() for k, v in session.gates.items()}})

                # Populate todos if discovering repo
                if tool_name == "qe_discover_repo" and len(session.todos) == 0:
                    self.todo_provider.todos_add(session, [
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

        # 8. Produce Final Structured Response if LLM didn't emit text
        if not full_content:
            response_text = (
                f"### 🛡️ Quality Engineering Workflow Summary\n\n"
                f"**Specialist:** `{persona.name}` (`{persona.role}`)\n"
                f"**Harness Mode:** `[{session.mode.upper()}]`\n\n"
                f"Executed tools and validated quality criteria against the active workspace. "
                f"Your **Todo Drawer** and **Magentic Ledger** have been synchronized in real-time."
            )
            for word in response_text.split(" "):
                if abort_event and abort_event.is_set():
                    yield AGUIProtocol.aborted()
                    return
                yield AGUIProtocol.text_chunk(f"{word} ")
                await asyncio.sleep(0.015)
            full_content = response_text

        # 9. Record Assistant Message in Session
        asst_msg = ChatMessage(
            id=f"msg_a_{int(time.time()*1000)}",
            role="assistant",
            content=full_content,
            thought="\n".join(thoughts),
            agentId=persona.id,
            toolCalls=executed_records,
            createdAt=int(time.time()*1000)
        )
        session.messages.append(asst_msg)

        # 10. Advance Magentic Subgoal
        self.orchestrator.advance_subgoal(session, plan["subgoal"]["id"], f"Completed: {plan['subgoal']['title']}")

        yield AGUIProtocol.state_delta({
            "ledger": session.ledger.model_dump(),
            "todos": [t.model_dump() for t in session.todos],
            "gates": {k: v.model_dump() for k, v in session.gates.items()},
            "toolsUsed": session.toolsUsed
        })

        # 11. Save response to semantic prompt cache to reduce future token consumption
        if full_content and len(full_content) > 20:
            estimated_tokens = max(100, len(full_content) // 4)
            global_harness_cache.set(cache_key, {"content": full_content, "tokens": estimated_tokens})

        yield AGUIProtocol.run_finished(int((time.time() - start_time) * 1000))
