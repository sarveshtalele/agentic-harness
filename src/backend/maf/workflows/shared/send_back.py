"""Review every item, send each REJECT back once to its agent, and review only those again."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable

from backend.core.errors import AllowanceError
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.shared.review import _review_budget_left, review_cases


async def review_with_send_back(rc: RunContext, kind: str, label: str, entries: list[tuple[str, str]], evidence_for: Callable[[list[int]], str], source: Path | None,
                                revise: Callable[[int, dict, list[AgentCall]], Awaitable[str]], batch: int = 8) -> tuple[list[dict], dict]:
    """Reviews every item, sends each REJECT back alone to its agent, once, and reviews only those again. REVISE is never sent back, to control tokens.

    `revise(index, record, calls)` returns the new text of that item, or raises, and appends every AgentCall it makes to `calls` so failed attempts are counted too. A failed revision leaves the item as it was, still REJECT and shown.
    """
    index = {key: i for i, (key, _) in enumerate(entries)}
    records, spent = await review_cases(rc, kind, label, entries, lambda keys: evidence_for([index[k] for k in keys]), source, batch)
    tokens = {"review": spent, "revise": 0}
    rejected = [i for i, record in enumerate(records) if record["verdict"] == "REJECT"] if _review_budget_left(rc) else []
    revised: dict[int, str] = {}
    revise_calls: list[AgentCall] = []
    if rejected:
        outcomes = await asyncio.gather(*(revise(i, records[i], revise_calls) for i in rejected), return_exceptions=True)
        for i, outcome in zip(rejected, outcomes):
            if isinstance(outcome, BaseException) and not isinstance(outcome, Exception):
                raise outcome
            if isinstance(outcome, AllowanceError):
                raise outcome
            if isinstance(outcome, Exception):
                rc.log(f"{entries[i][0]} could not be revised after review: {str(outcome)[:200]}", kind="warning")
                records[i]["problems"] = [*records[i].get("problems", []), f"Sent back once, but the revision failed: {str(outcome)[:200]}"]
                records[i]["round"] = 1
            else:
                revised[i] = outcome
        if revised:
            again = [(entries[i][0], text) for i, text in revised.items()]
            second, spent = await review_cases(rc, kind, label, again, lambda keys: evidence_for([index[k] for k in keys]), source, batch)
            tokens["review"] += spent
            for i, record in zip(revised, second):
                first = records[i]
                if record["status"] == "NOT RUN":  # the first REJECT stays visible rather than turning into a blank
                    first["problems"] = [*first.get("problems", []), "Revised once, but the second review did not run, so this is the first review"]
                    continue
                records[i] = {**record, "round": 2, "first_round": {"total": first.get("total"), "verdict": first["verdict"], "flaws": first.get("flaws", [])}}
    tokens["revise"] = sum(call.tokens for call in revise_calls)
    for record in records:
        record.setdefault("round", 1)
    tokens["total"] = tokens["review"] + tokens["revise"]
    sent = len(rejected)
    rc.log(f"Confidence review of {label}: {len(records)} items, {sent} sent back once, {sum(1 for r in records if r['verdict'] == 'REJECT')} still REJECT, {tokens['total']} tokens ({tokens['review']} review, {tokens['revise']} revision)",
           {"tokens": tokens, "sent_back": [entries[i][0] for i in rejected]}, "review")
    return records, tokens
