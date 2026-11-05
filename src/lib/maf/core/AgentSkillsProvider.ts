export interface SkillDefinition {
  name: string;
  description: string;
  category: "planning" | "design" | "generation" | "execution" | "healing" | "governance";
  associatedGate?: number;
  triggerCommand: string;
  leadAgent: string;
}

/**
 * MAF AgentSkillsProvider (agent-framework.pdf pp. 162-180)
 * Manages the catalog of specialized QE skills mapped from agentic-qe.
 */
export class AgentSkillsProvider {
  private skills: SkillDefinition[] = [
    {
      name: "qe-discover",
      description: "Scans repository AST, detects frameworks, extracts public endpoints and components.",
      category: "planning",
      associatedGate: 1,
      triggerCommand: "$qe-discover",
      leadAgent: "repo-intelligence-analyst",
    },
    {
      name: "qe-requirements",
      description: "Extracts acceptance criteria, business rules, and behavioral contracts from specs.",
      category: "planning",
      associatedGate: 1,
      triggerCommand: "$qe-requirements",
      leadAgent: "repo-intelligence-analyst",
    },
    {
      name: "qe-plan",
      description: "Formulates risk-based test strategy and allocates tests across Unit, Integration, and E2E levels.",
      category: "planning",
      associatedGate: 2,
      triggerCommand: "$qe-plan",
      leadAgent: "principal-test-architect",
    },
    {
      name: "qe-design",
      description: "Designs deterministic test cases with valid inputs, expected contracts, and mock boundaries.",
      category: "design",
      associatedGate: 3,
      triggerCommand: "$qe-design",
      leadAgent: "test-design-architect",
    },
    {
      name: "qe-data",
      description: "Generates realistic synthetic test data and fixtures conforming to real types.",
      category: "design",
      associatedGate: 3,
      triggerCommand: "$qe-data",
      leadAgent: "test-design-architect",
    },
    {
      name: "qe-generate",
      description: "Generates 1:1 compilable test code in Playwright, Vitest, PyTest, or JUnit.",
      category: "generation",
      associatedGate: 4,
      triggerCommand: "$qe-generate",
      leadAgent: "test-automation-engineer",
    },
    {
      name: "qe-execute",
      description: "Runs tests in isolated environments with approved runners and captures JUnit metrics.",
      category: "execution",
      associatedGate: 5,
      triggerCommand: "$qe-execute",
      leadAgent: "qa-execution-engineer",
    },
    {
      name: "qe-heal",
      description: "Autonomous test healing: repairs drifted selectors and fixtures without weakening assertions.",
      category: "healing",
      associatedGate: 6,
      triggerCommand: "$qe-heal",
      leadAgent: "defect-diagnostician",
    },
    {
      name: "qe-trace",
      description: "Traces test cases against requirements, audits code coverage gaps, and flags missed paths.",
      category: "governance",
      associatedGate: 7,
      triggerCommand: "$qe-trace",
      leadAgent: "coverage-auditor",
    },
    {
      name: "qe-sign",
      description: "Calculates independent confidence score (0-100) and issues final release sign-off.",
      category: "governance",
      associatedGate: 8,
      triggerCommand: "$qe-sign",
      leadAgent: "confidence-reviewer",
    },
    {
      name: "qe-panel",
      description: "Renders the live interactive QE status dashboard and quality ledger.",
      category: "governance",
      triggerCommand: "$qe-panel",
      leadAgent: "principal-test-architect",
    },
  ];

  public getSkills(): SkillDefinition[] {
    return [...this.skills];
  }

  public getSkillByTrigger(trigger: string): SkillDefinition | undefined {
    return this.skills.find(
      (s) => s.triggerCommand === trigger || s.name === trigger
    );
  }

  public getPromptSkillCatalog(): string {
    const lines = this.skills.map(
      (s) => `- ${s.name} (${s.triggerCommand}): ${s.description} [Lead: ${s.leadAgent}]`
    );
    return `[AVAILABLE QE SKILLS]\n${lines.join("\n")}`;
  }
}
