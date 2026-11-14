"""Gate A design: the solution architect's note, checked by code. Nothing here wires Gate A into the workflow; the workflow calls design_architecture."""
from __future__ import annotations

import json

from backend.qe import stacks
from backend.qe.model.schemas import ArchitectureNote
from backend.qe.stacks import StackError

MAX_ROUNDS = 2


def check_architecture(note: ArchitectureNote, requirement_ids: list[str]) -> ArchitectureNote:
    """Refuse an unknown stack, a requirement id nobody was given, or a requirement no module covers. Returns the note when it holds."""
    stacks.load(note.stack_id)  # StackError names the templates
    known, given = set(requirement_ids), set()
    items = [*note.modules, *note.data_model, *note.api_routes, *note.pages]
    for item in items:
        given.update(item.requirement_ids)
    invented = sorted(given - known)
    if invented:
        raise StackError(f"The note names requirement ids that were not given: {', '.join(invented)}")
    uncovered = sorted(known - {i for m in note.modules for i in m.requirement_ids})
    if uncovered:
        raise StackError(f"No module covers these requirements: {', '.join(uncovered)}")
    if note.pages and not stacks.load(note.stack_id).ui:
        raise StackError(f"Stack {note.stack_id} has no web page, so the note cannot list pages")
    return note


async def design_architecture(run_id: str | None, project_id: str, requirements: list[dict]) -> ArchitectureNote:
    """Ask the solution-architect for the note; a refusal goes back to it once with the reason. Still refused: StackError."""
    from backend.maf.runtime import AgentCall

    ids = [r["id"] for r in requirements]
    catalog = [{"id": s.id, "name": s.name, "language": s.language, "ui": s.ui} for s in stacks.list_templates()]
    base = f"STACK TEMPLATES (stack_id must be one of these ids):\n{json.dumps(catalog)}\n\nREQUIREMENTS:\n{json.dumps(requirements)}"
    message = f"Design the architecture note for these requirements.\n{base}"
    for round_ in range(MAX_ROUNDS):
        note = await AgentCall(run_id, project_id, "solution-architect").typed(message, ArchitectureNote, attempts=2)
        try:
            return check_architecture(note, ids)
        except StackError as exc:
            if round_ + 1 == MAX_ROUNDS:
                raise
            message = f"Your note was refused: {exc}\nSend the full corrected note.\n{base}"
    raise AssertionError("unreachable")
