"""The create_skill agent tool (HS-10): a Skill Studio draft plan from the chat. A human approves it in the Studio."""
from __future__ import annotations

import json
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from backend.core.errors import AqeError
from backend.core.skill_studio import author, steps
from backend.maf.tools.common import owned_document

DRAFT = "The plan is a draft. Review and approve it in Skill Studio; nothing is generated or published until you approve there."


def build(project_id: str):
    @tool(name="create_skill", description="Plan a new agent skill in Skill Studio from the user's request or a project document. "
                                           "Writes a draft plan only; a human approves, generates and publishes it in Skill Studio.")
    async def create_skill(
        request: Annotated[str, Field(description="What the skill should do, in the user's words")],
        kind: Annotated[Literal["instructions", "scripts"], Field(description="instructions: SKILL.md and references; scripts: also Python scripts with tests")] = "instructions",
        document_id: Annotated[str, Field(description="A project document to use as the source; empty uses the request text")] = "",
    ) -> str:
        try:
            if document_id:
                owned_document(project_id, document_id)  # only this project's documents
            source = {"type": "document", "document_id": document_id} if document_id else {"type": "text", "text": request}
            made = await steps.propose(project_id, kind, request, source)  # the same checks and call as POST /api/skill-studio/plans
        except KeyError as exc:
            return f"No plan created: not found: {exc.args[0] if exc.args else ''}"
        except (ValueError, AqeError, author.ReplyRejected) as exc:  # no permission, empty source, no model, a rejected reply
            return f"No plan created: {exc}"
        plan = made["plan"]
        return json.dumps({"plan_id": made["id"], "status": made["status"], "name": plan["name"], "description": plan["description"],
                           "tasks": len(plan["tasks"]), "subagents": len(plan["subagents"]), "eval_cases": len(plan["eval_cases"]),
                           "studio_url": f"/skills/studio?plan={made['id']}", "note": DRAFT})

    return create_skill
