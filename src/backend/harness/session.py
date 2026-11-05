import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TodoItem(BaseModel):
    id: str
    title: str
    status: str = "pending"  # pending, in_progress, completed, failed
    createdAt: int
    completedAt: Optional[int] = None
    agentId: Optional[str] = None

class ToolCallRecord(BaseModel):
    id: str
    name: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    status: str = "pending"
    error: Optional[str] = None
    gateNumber: Optional[int] = None

class GateApprovalInfo(BaseModel):
    gateNumber: int
    gateName: str
    confidenceScore: int = 90
    confidenceVerdict: str = "APPROVED"
    artifactSummary: str
    evidenceCitations: List[str] = Field(default_factory=list)
    status: str = "pending"
    feedback: Optional[str] = None

class ChatMessage(BaseModel):
    id: str
    role: str  # user, assistant, system, tool
    content: str
    thought: Optional[str] = None
    agentId: Optional[str] = None
    toolCalls: List[ToolCallRecord] = Field(default_factory=list)
    toolCallId: Optional[str] = None
    createdAt: int
    gateApproval: Optional[GateApprovalInfo] = None

class MagenticSubgoal(BaseModel):
    id: str
    title: str
    done: bool = False
    assignedAgent: str

class MagenticLedger(BaseModel):
    taskLedger: Dict[str, Any] = Field(default_factory=lambda: {
        "goal": "Formulate and execute complete Agentic QE campaign",
        "subgoals": [
            {"id": "sg-1", "title": "Analyze repository AST & extract interfaces", "done": False, "assignedAgent": "repo-intelligence-analyst"},
            {"id": "sg-2", "title": "Formulate level-allocated test strategy & risk ranking", "done": False, "assignedAgent": "principal-test-architect"},
            {"id": "sg-3", "title": "Design deterministic test cases with fixtures", "done": False, "assignedAgent": "test-design-architect"},
            {"id": "sg-4", "title": "Generate 1:1 compilable test automation code", "done": False, "assignedAgent": "test-automation-engineer"},
            {"id": "sg-5", "title": "Execute sandboxed test suites & parse JUnit", "done": False, "assignedAgent": "qa-execution-engineer"},
            {"id": "sg-6", "title": "Autonomous healing & assertion verification", "done": False, "assignedAgent": "defect-diagnostician"},
            {"id": "sg-7", "title": "Coverage audit & confidence score sign-off", "done": False, "assignedAgent": "confidence-reviewer"},
        ],
        "constraints": [
            "Never weaken test assertions during healing",
            "Prefer lowest level of test that proves behavior",
            "Maintain 1:1 case traceability"
        ]
    })
    progressLedger: Dict[str, Any] = Field(default_factory=lambda: {
        "completedSteps": [],
        "currentSubgoal": "sg-1: Analyze repository AST & extract interfaces",
        "blockers": []
    })
    stallCount: int = 0
    isStalled: bool = False

class GateState(BaseModel):
    gateNumber: int
    name: str
    status: str = "not_started"  # not_started, pending, approved, rejected
    score: Optional[int] = None
    updatedAt: int

class SessionState(BaseModel):
    id: str
    name: str
    workingDir: str
    mode: str = "plan"  # plan or execute
    activeAgentId: str = "principal-test-architect"
    systemPrompt: Optional[str] = None
    projectId: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    todos: List[TodoItem] = Field(default_factory=list)
    ledger: MagenticLedger = Field(default_factory=MagenticLedger)
    gates: Dict[str, GateState] = Field(default_factory=lambda: {
        "1": GateState(gateNumber=1, name="Discovery & Requirements", status="not_started", updatedAt=int(time.time()*1000)),
        "2": GateState(gateNumber=2, name="Test Strategy & Risk Allocation", status="not_started", updatedAt=int(time.time()*1000)),
        "3": GateState(gateNumber=3, name="Deterministic Test Design", status="not_started", updatedAt=int(time.time()*1000)),
        "4": GateState(gateNumber=4, name="Test Code Generation", status="not_started", updatedAt=int(time.time()*1000)),
        "5": GateState(gateNumber=5, name="Isolated Test Execution", status="not_started", updatedAt=int(time.time()*1000)),
        "6": GateState(gateNumber=6, name="Autonomous Healing & Assertion Guard", status="not_started", updatedAt=int(time.time()*1000)),
        "7": GateState(gateNumber=7, name="Coverage & Traceability Audit", status="not_started", updatedAt=int(time.time()*1000)),
        "8": GateState(gateNumber=8, name="Release Confidence Sign-off", status="not_started", updatedAt=int(time.time()*1000)),
    })
    toolsUsed: Dict[str, int] = Field(default_factory=dict)
    createdAt: int
    updatedAt: int

class AgentSessionManager:
    """
    Manages persistent sessions on disk (DeepSeek-style JSON persistence in .sessions/)
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(os.getcwd(), ".sessions")
        os.makedirs(self.base_dir, exist_ok=True)

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        if not os.path.exists(self.base_dir):
            return []
        for fname in os.listdir(self.base_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.base_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        sessions.append({
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "mode": data.get("mode"),
                            "activeAgentId": data.get("activeAgentId"),
                            "projectId": data.get("projectId") or "prj_agentic_qe",
                            "messagesCount": len(data.get("messages", [])),
                            "todosCount": len(data.get("todos", [])),
                            "updatedAt": data.get("updatedAt", 0),
                            "createdAt": data.get("createdAt", 0),
                        })
                except Exception:
                    continue
        return sorted(sessions, key=lambda s: s["updatedAt"], reverse=True)

    def get_session(self, session_id: str) -> Optional[SessionState]:
        fpath = os.path.join(self.base_dir, f"{session_id}.json")
        if not os.path.exists(fpath):
            return None
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return SessionState(**data)
        except Exception as e:
            print(f"[MAF Session] Error loading session {session_id}: {e}")
            return None

    def save_session(self, session: SessionState) -> None:
        fpath = os.path.join(self.base_dir, f"{session.id}.json")
        session.updatedAt = int(time.time() * 1000)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(session.model_dump_json(indent=2))
        except Exception as e:
            print(f"[MAF Session] Error saving session {session.id}: {e}")

    def create_session(self, name: Optional[str] = None, mode: str = "plan", project_id: Optional[str] = None) -> SessionState:
        now = int(time.time() * 1000)
        sess_id = f"sess_{now}_{os.urandom(3).hex()}"
        sess_name = name or f"QE Session #{len(self.list_sessions()) + 1}"
        session = SessionState(
            id=sess_id,
            name=sess_name,
            workingDir=os.getcwd(),
            mode=mode,
            projectId=project_id,
            createdAt=now,
            updatedAt=now
        )
        self.save_session(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        fpath = os.path.join(self.base_dir, f"{session_id}.json")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                return True
            except Exception:
                return False
        return False
