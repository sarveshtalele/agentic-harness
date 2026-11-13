"""Brainstorm workflow (docs/PHASE2_PLAN.md R3, 12.4): from a stated need and sources to a signed BRD, one question at a time.

Look before asking (the sources are read first); one question per round, with why it is asked and where it came from;
a play-back of what is understood so far, which the analyst may edit with the question; then two or three approaches
the analyst picks from; then the BRD draft, the independent review, a builder check (at most one round of questions only
the analyst can answer), Gherkin, and Gate 1. Each human step is a MAF request_info approval, so a run survives a
restart and every answer is a recorded decision by a named person.
The method is adapted from obra/superpowers skills/brainstorming (MIT, Copyright 2025 Jesse Vincent; see
docs/THIRD_PARTY_NOTICES.md); its browser companion is not ported, BA Studio is the companion.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from pydantic import BaseModel

from backend.maf.engine import REGISTRY, Definition, RunContext, StageSpec
from backend.maf.runtime import AgentCall
from backend.maf.workflows.ba import ba_approved, ba_context, ba_draft, ba_gate, ba_gherkin, ba_review
from backend.maf.workflows.shared import intake, intake_gate

MAX_QUESTIONS = 8
# What the model reads in HISTORY for a skipped or delegated question: an instruction, so it does not ask again (live run 2026-11-13)
ACTIONS = {"skip": "(not known yet: list it under Open Questions and do not ask it again)",
           "propose": "(the analyst asked you to decide: put your concrete answer in the play-back marked (proposed), and do not ask it again)"}


class Question(BaseModel):
    understood: str
    question: str = ""
    why: str = ""
    source: str = ""
    done: bool = False


class Approach(BaseModel):
    name: str
    summary: str
    tradeoffs: str


class Approaches(BaseModel):
    approaches: list[Approach]
    recommended: int = 0


class BuilderCheck(BaseModel):
    questions: list[str] = []


def _history(state: dict) -> str:
    return "\n".join(f"Q{n}: {h['question']}\nA{n}: {h['answer']}" for n, h in enumerate(state.get("history", []), 1)) or "(none yet)"


def _repeat_of(question: str, history: list[dict]) -> int:
    """The number of an earlier question this one repeats in other words, or 0 (live run 2026-11-13: the model re-asked)."""
    words = lambda t: {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 3}  # noqa: E731
    mine = words(question)
    for n, h in enumerate(history, 1):
        theirs = words(h["question"])
        overlap = len(mine & theirs) / max(1, len(mine | theirs))
        if overlap > 0.45 or SequenceMatcher(None, question.lower(), h["question"].lower()).ratio() > 0.65:  # tuned on the live run's repeats
            return n
    return 0


def _material(state: dict) -> str:
    return f"NEED:\n{state['need']}\n\nSOURCES:\n{state.get('source_text') or '(none)'}\n\nHISTORY:\n{_history(state)}"


async def bs_context(rc: RunContext, state: dict) -> dict:
    if not state.get("need", "").strip():
        raise ValueError("Describe what you need in one or two sentences")
    return {**await ba_context(rc, {**state, "brief": state["need"]}), "history": [], "asked": 0, "understood": ""}


async def bs_ask(rc: RunContext, state: dict) -> dict:
    if state["asked"] >= MAX_QUESTIONS:
        rc.log(f"{MAX_QUESTIONS} questions asked; moving on to approaches")
        return {"_next": "approaches"}
    call = AgentCall(rc.run_id, rc.project_id, "business-analyst", refs=())
    q = await call.typed(f"Artifact: brainstorm question.\n\n{_material(state)}", Question)
    if not q.done and (n := _repeat_of(q.question, state.get("history", []))):
        rc.log(f"The question repeats Q{n}; asking for a different one")
        q = await call.typed(f"Artifact: brainstorm question.\n\n{_material(state)}\n\nYour last question repeated Q{n}: {q.question}\n"
                             "Ask about something not yet in HISTORY, or set done to true.", Question)
        if not q.done and _repeat_of(q.question, state.get("history", [])):
            q.done = True  # a second repeat means nothing new is left to ask
    if q.done or not q.question.strip():
        rc.log("Nothing left open that would change the requirements", {"understood": q.understood})
        return {"understood": q.understood, "_next": "approaches"}
    rc.log(f"Question {state['asked'] + 1}: {q.question}", q.model_dump())
    return {"pending": q.model_dump(), "asked": state["asked"] + 1, "understood": q.understood}


async def bs_wait(rc: RunContext, state: dict) -> dict:
    return {}


def bs_question(rc: RunContext, state: dict) -> dict:
    q = state["pending"]
    return {"title": f"Brainstorm question {state['asked']}", "summary": q["question"],
            "payload": {"kind": "brainstorm_question", "round": state["asked"], **q, "history": state.get("history", [])}}


async def bs_answered(rc: RunContext, state: dict, answer: dict) -> dict:
    """The analyst's answer, or skip, or "propose something"; the question and play-back as they edited them."""
    q = {**state["pending"], **{k: answer[k] for k in ("question", "understood") if (answer.get(k) or "").strip()}}
    text = ACTIONS.get(answer.get("action", ""), "") or (answer.get("answer") or "").strip() or ACTIONS["skip"]
    rc.log(f"Answer to question {state['asked']}: {text}", {"question": q["question"]})
    return {"history": [*state.get("history", []), {"question": q["question"], "answer": text, "why": q.get("why", ""), "source": q.get("source", "")}],
            "understood": q["understood"], "pending": None}


async def bs_approaches(rc: RunContext, state: dict) -> dict:
    found = await AgentCall(rc.run_id, rc.project_id, "business-analyst", refs=()).typed(f"Artifact: approaches.\n\n{_material(state)}", Approaches)
    if not found.approaches:
        raise RuntimeError("The analyst agent proposed no approach")
    rc.log(f"{len(found.approaches)} approaches; recommended: {found.approaches[min(found.recommended, len(found.approaches) - 1)].name}", found.model_dump())
    return {"approaches": found.model_dump()}


def bs_pick(rc: RunContext, state: dict) -> dict:
    return {"title": "Pick an approach", "summary": "; ".join(a["name"] for a in state["approaches"]["approaches"]),
            "payload": {"kind": "brainstorm_approaches", **state["approaches"]}}


async def bs_picked(rc: RunContext, state: dict, answer: dict) -> dict:
    options = state["approaches"]["approaches"]
    choice = answer.get("choice")
    chosen = options[choice if isinstance(choice, int) and 0 <= choice < len(options) else min(state["approaches"]["recommended"], len(options) - 1)]
    rc.log(f"Approach chosen: {chosen['name']}", chosen)
    return {"approach": chosen}


async def bs_draft(rc: RunContext, state: dict) -> dict:
    a = state["approach"]
    brief = (f"{state['need']}\n\nWhat the analyst confirmed:\n{state.get('understood', '')}\n\nQuestions and answers:\n{_history(state)}\n\n"
             f"Chosen approach: {a['name']}. {a['summary']} Trade-offs: {a['tradeoffs']}")
    answers = state.get("builder_answers", "") if not state.get("builder_used") else ""  # the engine clears feedback after an approval
    drafted = await ba_draft(rc, {**state, "brief": brief, **({"feedback": answers} if answers else {})})
    return {**drafted, "brief": brief, "builder_used": bool(answers) or state.get("builder_used", False)}


async def bs_check(rc: RunContext, state: dict) -> dict:
    if state.get("checked"):
        return {}
    from backend.core import documents

    found = await AgentCall(rc.run_id, rc.project_id, "confidence-reviewer", skills=()).typed(
        f"Review type: builder check.\n\nDOCUMENT:\n{documents.get(state['doc_id'])['content']}\n\n{_material(state)}", BuilderCheck)
    rc.log(f"Builder check: {len(found.questions)} questions", found.model_dump())
    return {"builder_questions": found.questions[:5], "checked": True}


def bs_check_gate(rc: RunContext, state: dict) -> dict | None:
    questions = state.get("builder_questions") or []
    if not questions or state.get("builder_answered"):
        return None
    return {"title": "Questions from the builder check", "summary": f"{len(questions)} questions only you can answer",
            "payload": {"kind": "builder_check", "questions": questions, "document": state["doc_id"]}}


async def bs_check_answered(rc: RunContext, state: dict, answer: dict) -> dict:
    answers = answer.get("answers") or []
    lines = [f"Q: {q}\nA: {(answers[i] if i < len(answers) else '').strip() or '(not answered)'}" for i, q in enumerate(state["builder_questions"])]
    return {"builder_answered": True, "builder_answers": "The builder check asked, and the analyst answered:\n" + "\n".join(lines), "_next": "draft"}


def brainstorm_definition() -> Definition:
    return Definition("brainstorm", [
        StageSpec("intake", intake, "Intake", approval=intake_gate, next="context"),
        StageSpec("context", bs_context, "Read the sources", next="ask"),
        StageSpec("ask", bs_ask, "Next question", next="answer"),
        StageSpec("answer", bs_wait, "Analyst answers", approval=bs_question, on_approved=bs_answered, next="ask"),
        StageSpec("approaches", bs_approaches, "Approaches", approval=bs_pick, on_approved=bs_picked, next="draft"),
        StageSpec("draft", bs_draft, "Draft the BRD", next="review"),
        StageSpec("review", ba_review, "Independent review", next="check"),
        StageSpec("check", bs_check, "Builder check", approval=bs_check_gate, on_approved=bs_check_answered, next="gherkin"),
        StageSpec("gherkin", ba_gherkin, "Author Gherkin", approval=ba_gate, on_approved=ba_approved, on_rejected="draft", next="END"),
    ], routes={"ask": ["approaches"], "review": ["draft"], "check": ["draft"]})


REGISTRY["brainstorm"] = brainstorm_definition
