import {
  SessionState,
  ChatMessage,
  TodoItem,
  MagenticLedger,
  HarnessMode,
  GateState,
} from "../types";

/**
 * MAF AgentSession (agent-framework.pdf pp. 112-140)
 * Stateful session container encapsulating multi-turn conversation, StateBag,
 * Magentic ledger, and Quality Gate states.
 */
export class AgentSession {
  private state: SessionState;

  constructor(initialState?: Partial<SessionState>) {
    this.state = {
      id: initialState?.id || `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      name: initialState?.name || "QE Strategy & Test Campaign",
      workingDir: initialState?.workingDir || process.cwd(),
      mode: initialState?.mode || "plan",
      activeAgentId: initialState?.activeAgentId || "principal-test-architect",
      messages: initialState?.messages || [],
      todos: initialState?.todos || [],
      ledger: initialState?.ledger || {
        taskLedger: {
          goal: "Formulate and execute complete Agentic QE campaign",
          subgoals: [
            { id: "sg-1", title: "Analyze repository AST & extract interfaces", done: false, assignedAgent: "repo-intelligence-analyst" },
            { id: "sg-2", title: "Formulate level-allocated test strategy & risk ranking", done: false, assignedAgent: "principal-test-architect" },
            { id: "sg-3", title: "Design deterministic test cases with fixtures", done: false, assignedAgent: "test-design-architect" },
            { id: "sg-4", title: "Generate 1:1 compilable test automation code", done: false, assignedAgent: "test-automation-engineer" },
            { id: "sg-5", title: "Execute sandboxed test suites & parse JUnit", done: false, assignedAgent: "qa-execution-engineer" },
            { id: "sg-6", title: "Autonomous healing & assertion verification", done: false, assignedAgent: "defect-diagnostician" },
            { id: "sg-7", title: "Coverage audit & confidence score sign-off", done: false, assignedAgent: "confidence-reviewer" },
          ],
          constraints: [
            "Never weaken test assertions during healing",
            "Prefer lowest level of test that proves behavior",
            "Maintain 1:1 case traceability",
          ],
        },
        progressLedger: {
          completedSteps: [],
          currentSubgoal: "sg-1: Analyze repository AST & extract interfaces",
          blockers: [],
        },
        stallCount: 0,
        isStalled: false,
      },
      gates: initialState?.gates || {
        1: { gateNumber: 1, name: "Discovery & Requirements", status: "not_started", updatedAt: Date.now() },
        2: { gateNumber: 2, name: "Test Strategy & Risk Allocation", status: "not_started", updatedAt: Date.now() },
        3: { gateNumber: 3, name: "Deterministic Test Design", status: "not_started", updatedAt: Date.now() },
        4: { gateNumber: 4, name: "Test Code Generation", status: "not_started", updatedAt: Date.now() },
        5: { gateNumber: 5, name: "Isolated Test Execution", status: "not_started", updatedAt: Date.now() },
        6: { gateNumber: 6, name: "Autonomous Healing & Assertion Guard", status: "not_started", updatedAt: Date.now() },
        7: { gateNumber: 7, name: "Coverage & Traceability Audit", status: "not_started", updatedAt: Date.now() },
        8: { gateNumber: 8, name: "Release Confidence Sign-off", status: "not_started", updatedAt: Date.now() },
      },
      createdAt: initialState?.createdAt || Date.now(),
      updatedAt: initialState?.updatedAt || Date.now(),
    };
  }

  public getState(): SessionState {
    return { ...this.state };
  }

  public getId(): string {
    return this.state.id;
  }

  public getMode(): HarnessMode {
    return this.state.mode;
  }

  public setMode(mode: HarnessMode): void {
    this.state.mode = mode;
    this.state.updatedAt = Date.now();
  }

  public getActiveAgentId(): string {
    return this.state.activeAgentId;
  }

  public setActiveAgentId(agentId: string): void {
    this.state.activeAgentId = agentId;
    this.state.updatedAt = Date.now();
  }

  public getMessages(): ChatMessage[] {
    return [...this.state.messages];
  }

  public appendMessage(message: ChatMessage): void {
    this.state.messages.push(message);
    this.state.updatedAt = Date.now();
  }

  public updateMessage(messageId: string, delta: Partial<ChatMessage>): void {
    const idx = this.state.messages.findIndex((m) => m.id === messageId);
    if (idx !== -1) {
      this.state.messages[idx] = { ...this.state.messages[idx], ...delta };
      this.state.updatedAt = Date.now();
    }
  }

  public getTodos(): TodoItem[] {
    return [...this.state.todos];
  }

  public setTodos(todos: TodoItem[]): void {
    this.state.todos = todos;
    this.state.updatedAt = Date.now();
  }

  public getLedger(): MagenticLedger {
    return { ...this.state.ledger };
  }

  public updateLedger(delta: Partial<MagenticLedger>): void {
    this.state.ledger = {
      ...this.state.ledger,
      ...delta,
      taskLedger: delta.taskLedger ? { ...this.state.ledger.taskLedger, ...delta.taskLedger } : this.state.ledger.taskLedger,
      progressLedger: delta.progressLedger ? { ...this.state.ledger.progressLedger, ...delta.progressLedger } : this.state.ledger.progressLedger,
    };
    this.state.updatedAt = Date.now();
  }

  public getGates(): Record<number, GateState> {
    return { ...this.state.gates };
  }

  public updateGate(gateNumber: number, delta: Partial<GateState>): void {
    if (this.state.gates[gateNumber]) {
      this.state.gates[gateNumber] = {
        ...this.state.gates[gateNumber],
        ...delta,
        updatedAt: Date.now(),
      };
      this.state.updatedAt = Date.now();
    }
  }

  public updateState(delta: Partial<SessionState>): void {
    this.state = {
      ...this.state,
      ...delta,
      updatedAt: Date.now(),
    };
  }

  public toJSON(): SessionState {
    return this.getState();
  }

  public static fromJSON(json: SessionState): AgentSession {
    return new AgentSession(json);
  }
}
