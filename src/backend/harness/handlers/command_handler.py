"""
Slash Command Handler for Agentic QE Harness.
Handles /mode, /todos, /gates, /skills, /approvals, /ast, and /help.
"""
from typing import AsyncGenerator, Dict, Any, Optional
from backend.harness.session import SessionState, ChatMessage
from backend.harness.agui_protocol import AGUIProtocol


async def handle_harness_command(
    cmd: str,
    arg: str,
    prompt_trimmed: str,
    session: SessionState,
    skill_discovery: Any,
    mode_provider: Any,
    todo_provider: Any,
    now: int
) -> AsyncGenerator[str, None]:
    """
    Executes standard harness slash commands and yields AG-UI SSE protocol chunks.
    """
    if cmd in ("/help", "/h", "/?"):
        help_md = (
            "### 🛠️ Agentic QE Platform Harness Commands\n\n"
            "| Command | Description |\n"
            "| :--- | :--- |\n"
            "| `/create_agent_skill <name>` | Synthesize & package a standardized Agent Skill |\n"
            "| `/doc <topic>` | Generate full 10-section BRD/PRD with Gherkin acceptance criteria |\n"
            "| `/skills` | Browse all authentic project and plugin skills |\n"
            "| `/plan [scope]` | Switch to **[PLAN MODE]** and formulate test strategy |\n"
            "| `/execute [tests]` | Switch to **[EXECUTE MODE]** and run test suites |\n"
            "| `/mode <plan|execute>` | Explicitly toggle Plan vs. Execute mode |\n"
            "| `/todos` | View active session task ledger |\n"
            "| `/gates` | Inspect status of all 8 Quality Gates |\n"
            "| `/approvals` | List pending Human-in-the-Loop approvals |\n"
            "| `/security-audit` | Run Cloudflare & NVIDIA Skill Specter security audit |\n"
            "| `/discover` | Inspect workspace AST, routes, and test frameworks |\n"
            "| `/heal` | Diagnose failed tests and heal drifted selectors |\n"
        )
        user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
        asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=help_md, createdAt=now+1)
        session.messages.extend([user_msg, asst_msg])
        yield AGUIProtocol.text_chunk(help_md)
        yield AGUIProtocol.run_finished(100)
        return

    elif cmd in ("/mode", "/m"):
        target_mode = arg.lower()
        if target_mode in ("plan", "execute"):
            session.mode = target_mode
            mode_provider.set_mode(target_mode)
            mode_msg = f"Switched harness mode to **[{target_mode.upper()} MODE]**.\n"
            user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
            asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=mode_msg, createdAt=now+1)
            session.messages.extend([user_msg, asst_msg])
            yield AGUIProtocol.state_delta({"mode": target_mode})
            yield AGUIProtocol.text_chunk(mode_msg)
            yield AGUIProtocol.run_finished(100)
        return

    elif cmd in ("/todos", "/tasks", "/todo"):
        todos_list = session.todos
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
            "### 🛡️ 8 Quality Engineering Gates Status\n\n"
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

    elif cmd in ("/plugin", "/plugins"):
        target = arg.lower() or "agentic-qe"
        plugin_info = (
            f"### 🔌 Plugin: `agentic-qe`\n\n"
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
        all_local_skills = skill_discovery.list_skills()
        if not arg:
            by_category: Dict[str, list] = {}
            for s in all_local_skills:
                by_category.setdefault(s["category"], []).append(s)

            cat_sections = []
            for cat_name, s_list in by_category.items():
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
                f"Dynamically indexed from your local machine across `skills/` and agent plugins.\n\n"
                + "\n".join(cat_sections) +
                f"\n💡 *Invoke any skill directly using:* `/<skill-name>` (e.g. `/skill-creator`, `/analyzing-repositories`, `/security-audit`)\n"
            )
            user_msg = ChatMessage(id=f"msg_u_{now}", role="user", content=prompt_trimmed, createdAt=now)
            asst_msg = ChatMessage(id=f"msg_a_{now+1}", role="assistant", content=skills_catalog, createdAt=now+1)
            session.messages.extend([user_msg, asst_msg])
            yield AGUIProtocol.text_chunk(skills_catalog)
            yield AGUIProtocol.run_finished(120)
            return
