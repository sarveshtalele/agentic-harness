"""Command Line Interface (CLI) for Agentic QE Harness.
Allows running the complete MAF 2.0 Harness directly from terminal/headless environments
without requiring the Web UI.

Usage:
  bin/harness [command or prompt]
  bin/harness /skills
  bin/harness /projects
  bin/harness /project <id>
  bin/harness /gates
  bin/harness /audit
  bin/harness
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

# Ensure src is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend import config, db
from backend.core.seed_data import seed_database
from backend.harness.discovery import LocalSkillDiscovery
from backend.harness.harness_agent import HarnessAgent
from backend.harness.llm_config import LLMConfig, load_llm_config
from backend.harness.project_repository import global_project_repo
from backend.harness.session import AgentSessionManager, SessionState


# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║         ⚡ AGENTIC QE HARNESS — MAF 2.0 TERMINAL COMMAND CENTER     ║{RESET}")
    print(f"{CYAN}{BOLD}╚═══════════════════════════════════════════════════════════════════╝{RESET}")
    print(f"{DIM}Autonomous Quality Engineering · 58 Local Skills · SQLite WAL Knowledge Base{RESET}\n")


async def run_prompt_stream(harness: HarnessAgent, session: SessionState, prompt: str, llm_conf: LLMConfig):
    """Streams the agent output directly to stdout in real-time."""
    in_thought = False
    async for sse_chunk in harness.run(session, prompt, llm_conf):
        for line in sse_chunk.splitlines():
            line = line.strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            try:
                event = json.loads(payload)
                ev_type = event.get("type")
                if ev_type == "TEXT_CHUNK":
                    if in_thought:
                        print(f"{RESET}")
                        in_thought = False
                    sys.stdout.write(event.get("chunk", ""))
                    sys.stdout.flush()
                elif ev_type == "THOUGHT_CHUNK":
                    if not in_thought:
                        print(f"{MAGENTA}{DIM}[Reasoning] ", end="")
                        in_thought = True
                    sys.stdout.write(event.get("thought", ""))
                    sys.stdout.flush()
                elif ev_type == "TOOL_INVOKED":
                    tool = event.get("tool", {})
                    print(f"\n{YELLOW}⚙️  Invoking Tool: {tool.get('name')} {DIM}{tool.get('args')}{RESET}")
                elif ev_type == "GATE_APPROVAL_REQUIRED":
                    appr = event.get("approval", {})
                    print(f"\n{RED}{BOLD}🚨 Human Approval Required for Gate G{appr.get('gateNumber')}:{RESET} {appr.get('title')}")
                elif ev_type == "AGENT_SWITCH":
                    print(f"\n{BLUE}🔄 Handoff to Agent: {BOLD}{event.get('targetAgent')}{RESET}")
                elif ev_type == "RUN_FINISHED":
                    if in_thought:
                        print(f"{RESET}")
                        in_thought = False
                    print(f"\n{DIM}✓ Execution finished in {event.get('durationMs', 0)}ms{RESET}\n")
            except Exception:
                pass


def repl(harness: HarnessAgent, session_manager: AgentSessionManager, llm_conf: LLMConfig):
    """Interactive Read-Eval-Print Loop."""
    print_banner()
    session = session_manager.create_session("CLI Harness Session", "plan")
    skills_count = len(harness.skill_discovery.list_skills())
    projects = global_project_repo.list_projects()

    print(f"  {GREEN}●{RESET} Model: {BOLD}{llm_conf.model}{RESET}")
    print(f"  {GREEN}●{RESET} Mode: {YELLOW}[{session.mode.upper()}]{RESET}")
    print(f"  {GREEN}●{RESET} Local Skills: {BOLD}{skills_count}{RESET} loaded")
    print(f"  {GREEN}●{RESET} Registered Projects: {BOLD}{len(projects)}{RESET} in database")
    print(f"\nType {CYAN}/help{RESET} for commands or {CYAN}/exit{RESET} to quit.\n")

    while True:
        try:
            mode_badge = f"{YELLOW}[PLAN]{RESET}" if session.mode == "plan" else f"{GREEN}[EXECUTE]{RESET}"
            prompt_input = input(f"{BOLD}harness{RESET} {mode_badge} > ").strip()
            if not prompt_input:
                continue
            if prompt_input.lower() in ("/exit", "/quit", "exit", "quit"):
                print(f"\n{CYAN}Session saved. Exiting Agentic QE Harness. Goodbye!{RESET}")
                break
            
            asyncio.run(run_prompt_stream(harness, session, prompt_input, llm_conf))
            session_manager.save_session(session)
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{CYAN}Harness interrupted. Exiting.{RESET}")
            break


def main():
    parser = argparse.ArgumentParser(description="Agentic QE Terminal Harness")
    parser.add_argument("query", nargs="*", help="Optional command or query to execute immediately")
    parser.add_argument("--mode", choices=["plan", "execute"], default="plan", help="Execution mode")
    parser.add_argument("--model", help="LLM model override")
    args = parser.parse_args()

    # Ensure DB is migrated and seeded
    db.migrate()
    seed_database()

    llm_conf = load_llm_config()
    if args.model:
        llm_conf.model = args.model

    session_manager = AgentSessionManager()
    skill_discovery = LocalSkillDiscovery(ROOT_DIR)
    harness = HarnessAgent(ROOT_DIR, skill_discovery=skill_discovery)

    if args.query:
        full_query = " ".join(args.query).strip()
        session = session_manager.create_session("Single Run Session", args.mode)
        asyncio.run(run_prompt_stream(harness, session, full_query, llm_conf))
    else:
        repl(harness, session_manager, llm_conf)


if __name__ == "__main__":
    main()
