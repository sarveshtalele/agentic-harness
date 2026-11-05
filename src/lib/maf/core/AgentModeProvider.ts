import { HarnessMode, ToolDefinition } from "../types";

/**
 * MAF AgentModeProvider (agent-framework.pdf pp. 82-89)
 * Regulates tool execution and system prompting based on Plan vs Execute mode.
 */
export class AgentModeProvider {
  private mode: HarnessMode;

  constructor(initialMode: HarnessMode = "plan") {
    this.mode = initialMode;
  }

  public getMode(): HarnessMode {
    return this.mode;
  }

  public setMode(newMode: HarnessMode): void {
    this.mode = newMode;
  }

  /**
   * Evaluates if a tool can execute in the current mode.
   * Plan mode blocks write operations, code generation execution, and sandboxed test execution,
   * keeping the agent in an exploratory, strategy formulation posture.
   */
  public canExecuteTool(toolName: string, tool: ToolDefinition): { allowed: boolean; reason?: string } {
    if (this.mode === "execute") {
      return { allowed: true };
    }

    // Tools permitted in 'plan' mode: read, scan, analyze, design, and todo management
    const planModeAllowedPrefixes = [
      "read_",
      "glob",
      "grep",
      "todos_",
      "qe_discover",
      "qe_extract_requirements",
      "qe_plan_strategy",
      "qe_design_cases",
      "qe_confidence_review",
    ];

    const isExplicitlyAllowed = planModeAllowedPrefixes.some((prefix) =>
      toolName.startsWith(prefix)
    );

    if (isExplicitlyAllowed) {
      return { allowed: true };
    }

    return {
      allowed: false,
      reason: `Tool '${toolName}' produces side-effects or runs code, but Harness is currently in [Plan Mode]. Switch to [Execute Mode] or approve the plan to proceed.`,
    };
  }

  /**
   * System prompt guidance fragment injected based on current mode.
   */
  public getModePromptDirective(): string {
    if (this.mode === "plan") {
      return `\n[HARNESS MODE: PLAN MODE ACTIVE]
You are operating in PLAN MODE. Your objective is exploratory analysis, architecture formulation, test strategy planning, and case design. Do not execute tests or write source code directly yet. Formulate plans, register todos using 'todos_add', and prepare quality gates for human review.`;
    }
    return `\n[HARNESS MODE: EXECUTE MODE ACTIVE]
You are operating in EXECUTE MODE. You have authorization to generate test files, execute tests in sandboxed environments, heal broken selectors, and drive quality gates to completion. Always respect assertion preservation rules.`;
  }
}
