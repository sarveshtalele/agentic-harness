from typing import Dict, Any, Tuple

class AgentModeProvider:
    """
    MAF AgentModeProvider (agent-framework.pdf pp. 82-89)
    Regulates tool execution and system prompting based on Plan vs Execute mode.
    """
    def __init__(self, initial_mode: str = "plan"):
        self.mode = initial_mode

    def get_mode(self) -> str:
        return self.mode

    def set_mode(self, mode: str):
        if mode in ("plan", "execute"):
            self.mode = mode

    def can_execute_tool(self, tool_name: str) -> Tuple[bool, str]:
        """
        In Plan mode, destructive writes and runner executions are blocked.
        """
        if self.mode == "execute":
            return True, ""

        allowed_prefixes = [
            "read_",
            "glob",
            "grep",
            "todos_",
            "inspect_",
            "view_",
            "create_user_stories",
            "generate_gherkin",
            "create_document",
            "read_document",
            "check_gates",
            "scan_defects",
            "list_",
            "query_",
            "get_",
            "qe_discover",
            "qe_extract_requirements",
            "qe_plan_strategy",
            "qe_design_cases",
            "qe_confidence_review",
            "qe_security_audit",
        ]

        if any(tool_name.startswith(p) for p in allowed_prefixes):
            return True, ""

        return False, (
            f"Tool '{tool_name}' performs file modifications or executes code, "
            f"but Harness is currently in [Plan Mode]. Switch to [Execute Mode] in the UI or command composer to run it."
        )

    def get_prompt_directive(self) -> str:
        if self.mode == "plan":
            return (
                "\n[HARNESS MODE: PLAN MODE ACTIVE]\n"
                "You are operating in PLAN MODE. Your objective is exploratory analysis, architecture formulation, "
                "test strategy planning, and case design. Do not execute tests or write source code directly yet. "
                "Formulate plans, register todos using 'todos_add', and prepare quality gates for human review."
            )
        return (
            "\n[HARNESS MODE: EXECUTE MODE ACTIVE]\n"
            "You are operating in EXECUTE MODE. You have authorization to generate test files, execute tests "
            "in sandboxed environments, heal broken selectors, and drive quality gates to completion. "
            "Always respect the Assertion Preservation Rule."
        )
