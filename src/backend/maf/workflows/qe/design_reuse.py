"""A Gate 3 send-back redesigns only the requirements its feedback names. The others keep their cases, reviews and audit verdicts."""
from __future__ import annotations

import re


def _names(text: str, ids) -> set[str]:
    return {i for i in ids if re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text)}


def reusable(state: dict, designed: list[dict], quota: dict[str, int]) -> dict[str, list[tuple[dict, dict, dict | None]]]:
    """{requirement id: [(case, review record, audit verdict)]} for the requirements to keep. Empty (design everything again) when there is no earlier
    design or the feedback names no requirement or case, because then it may be about any of them."""
    kept = state.get("design_kept") or {}
    earlier = kept.get("cases", [])
    text = state.get("feedback", "")
    named = _names(text, {r["id"] for r in designed}) | {c["requirement_id"] for c in earlier if c["id"] in _names(text, {c["id"] for c in earlier})}
    if not named & {r["id"] for r in designed}:
        return {}
    keep = {}
    for r in designed:
        mine = [c for c in earlier if c["requirement_id"] == r["id"]]
        if r["id"] in named or not mine or len(mine) > quota.get(r["id"], 0) or any(c["id"] not in kept.get("records", {}) for c in mine):
            continue
        keep[r["id"]] = [(c, kept["records"][c["id"]], (kept.get("verdicts") or {}).get(c["id"])) for c in mine]
    return keep
