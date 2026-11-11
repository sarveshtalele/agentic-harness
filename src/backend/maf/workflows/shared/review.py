"""Independent confidence review: one artifact, or items in batches with code-checked records."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Callable

from backend.core.errors import AllowanceError
from backend.db import db
from backend.maf import runtime
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.qe import confidence, model


LOW_CONFIDENCE = 70


async def review_artifact(rc: RunContext, name: str, artifact: str, evidence: str = "") -> dict:
    """An independent score before a person approves. If the review cannot run, the result says so and carries no score."""
    try:
        review = await AgentCall(rc.run_id, rc.project_id, "confidence-reviewer", skills=()).typed(f"Review type: evidence. Score this {name} from the evidence.\n\nWORK:\n{artifact[:30_000]}\n\nEVIDENCE:\n{evidence[:25_000]}", model.ConfidenceReview)
    except AllowanceError:
        raise
    except RuntimeError as exc:
        rc.log(f"Confidence review of {name} did not run: {str(exc)[:200]}", kind="warning")
        return {"score": None, "verdict": "NOT RUN", "issues": [str(exc)[:300]]}
    rc.log(f"Confidence review of {name}: {review.score} ({review.verdict})", {"issues": review.issues}, "review")
    return review.model_dump()


def _id_of(text: str) -> str:
    found = re.search(r'"id":\s*"([^"]+)"', text)
    return found.group(1) if found else ""


def _review_budget_left(rc: RunContext) -> bool:
    """Reviews stop first when tokens run low, so a run can still generate and run its tests. A third of the run's limit is kept for that."""
    with db() as con:
        found = con.execute("SELECT tokens_in+tokens_out FROM runs WHERE id=?", (rc.run_id,)).fetchone()
    return not found or found[0] < runtime.RUN_TOKEN_LIMIT * 2 // 3


NOT_REVIEWED = "Not reviewed: the token budget is kept for generating and running tests"


async def review_cases(rc: RunContext, kind: str, label: str, entries: list[tuple[str, str]], evidence: str | Callable[[list[str]], str], source: Path | None, batch: int = 8) -> tuple[list[dict], int]:
    """Scores each item separately. Batches run together within the model limit. Code checks every record and recomputes totals and verdicts.

    `evidence` is a text, or a function of a batch's item keys. Returns one record per entry, in order, and the tokens used.
    A reply that cannot be used splits its batch in half, each half asked once more; items still unanswered are NOT RUN, with no score and no pass.
    """
    batches = [entries[i : i + batch] for i in range(0, len(entries), batch)]
    calls: list[AgentCall] = []
    norm = lambda key: re.sub(r"[\s\[\]]", "", str(key)).lower()

    async def ask(chunk: list[tuple[str, str]]) -> dict[str, dict]:
        """The checked records of the items the reviewer answered, by item key. An answer names the key, or the case's own id."""
        call = AgentCall(rc.run_id, rc.project_id, "confidence-reviewer", skills=())
        calls.append(call)
        shown = "\n\n".join(f"[{key}]\n{text}" for key, text in chunk)
        seen = evidence([key for key, _ in chunk]) if callable(evidence) else evidence
        review = await call.typed(f"Review type: {label}.\nScore each item below separately against the rubric for this review type. Send one record for every item, with the item's id (the text in square brackets, such as C1) as tc_id.\n\nITEMS:\n{shown}\n\nEVIDENCE:\n{seen[:40_000]}", confidence.Review, attempts=2)
        sent: dict[str, dict] = {}
        for item in review.items:
            sent.setdefault(norm(item.tc_id), item.model_dump())
        found = {}
        for key, text in chunk:
            raw = sent.get(norm(key)) or (sent.get(norm(own)) if (own := _id_of(text)) else None)
            if raw:
                found[key] = confidence.check_item({**raw, "tc_id": key}, kind, source)
        return found

    async def one(chunk: list[tuple[str, str]]) -> list[dict]:
        if not _review_budget_left(rc):
            rc.log(f"Confidence review of {label}: {NOT_REVIEWED}", {"items": [key for key, _ in chunk]}, "warning")
            return [confidence.not_run(key, kind, NOT_REVIEWED) for key, _ in chunk]
        try:
            found = await ask(chunk)
        except AllowanceError:
            raise
        except Exception as exc:
            if len(chunk) < 2:
                raise
            rc.log(f"Confidence review of {label}: a reply for {len(chunk)} items was unusable ({str(exc)[:160]}). Asking again in two halves", kind="warning")
            half = len(chunk) // 2
            parts = await asyncio.gather(ask(chunk[:half]), ask(chunk[half:]), return_exceptions=True)
            found = {}
            for part, sub in zip(parts, (chunk[:half], chunk[half:])):
                if isinstance(part, BaseException) and not isinstance(part, Exception):
                    raise part
                if isinstance(part, AllowanceError):
                    raise part
                if isinstance(part, Exception):  # only this half is lost
                    rc.log(f"Confidence review of {label} did not run for {len(sub)} items: {str(part)[:200]}", {"items": [key for key, _ in sub]}, "warning")
                    found |= {key: confidence.not_run(key, kind, str(part)) for key, _ in sub}
                else:
                    found |= part
        if missing := [(key, text) for key, text in chunk if key not in found]:
            try:  # a reviewer that leaves items out of a large batch is asked once more for just those
                found |= await ask(missing)
            except AllowanceError:
                raise
            except Exception as exc:
                rc.log(f"Confidence review of {label}: {len(missing)} items had no record and the second ask failed: {str(exc)[:160]}", kind="warning")
        return [found.get(key) or confidence.not_run(key, kind, "The reviewer sent no record for this item") for key, _ in chunk]

    outcomes = await asyncio.gather(*(one(chunk) for chunk in batches), return_exceptions=True)
    records: list[dict] = []
    for chunk, outcome in zip(batches, outcomes):
        if isinstance(outcome, BaseException) and not isinstance(outcome, Exception):
            raise outcome  # cancellation
        if isinstance(outcome, AllowanceError):
            raise outcome  # a limit is not a bad reply
        if isinstance(outcome, Exception):
            rc.log(f"Confidence review of {label} did not run for {len(chunk)} items: {str(outcome)[:200]}", {"items": [key for key, _ in chunk]}, "warning")
            records += [confidence.not_run(key, kind, str(outcome)) for key, _ in chunk]
        else:
            records += outcome
    return records, sum(call.tokens for call in calls)


def is_low(review: dict) -> bool:
    return review["score"] is not None and review["score"] < LOW_CONFIDENCE
