import time
import os
from typing import List, Dict, Any, Optional
from .session import SessionState, TodoItem

class TodoProvider:
    """
    MAF TodoProvider (agent-framework.pdf pp. 90-105)
    Manages active execution checklist for multi-step agentic workflows.
    """
    @staticmethod
    def todos_add(session: SessionState, tasks: List[str], agent_id: Optional[str] = None) -> List[TodoItem]:
        new_items = []
        now = int(time.time() * 1000)
        for t in tasks:
            todo = TodoItem(
                id=f"todo-{now}-{os.urandom(2).hex()}",
                title=t,
                status="pending",
                createdAt=now,
                agentId=agent_id or session.activeAgentId
            )
            session.todos.append(todo)
            new_items.append(todo)
        return new_items

    @staticmethod
    def todos_complete(session: SessionState, ids: List[str]) -> List[TodoItem]:
        completed = []
        now = int(time.time() * 1000)
        id_set = set(ids)
        for t in session.todos:
            matches_id = t.id in id_set
            matches_title = any(query.lower() in t.title.lower() for query in ids)
            if matches_id or matches_title:
                t.status = "completed"
                t.completedAt = now
                completed.append(t)
        return completed

    @staticmethod
    def todos_list(session: SessionState) -> Dict[str, Any]:
        return {
            "todos": [t.model_dump() for t in session.todos],
            "total": len(session.todos),
            "completed": len([t for t in session.todos if t.status == "completed"]),
            "pending": len([t for t in session.todos if t.status == "pending"]),
        }
