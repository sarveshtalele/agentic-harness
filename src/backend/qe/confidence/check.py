"""Checking cited evidence against the repository on disk."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from backend.core.security import PathEscape, safe_path
from backend.qe.confidence.rubric import ASSERTION_FLOOR, MAX_FILE_BYTES, RUBRIC, THRESHOLD, verdict_for
from backend.qe.confidence.summary import summarise


def parse_cite(text: Any) -> tuple[str, int, int] | None:
    """`path:line` or `path:line-line`, relative to the repository root; None when it has another shape."""
    found = re.fullmatch(r"([^:\s][^:]*):(\d+)(?:-(\d+))?", str(text or "").strip())
    return (found.group(1), int(found.group(2)), int(found.group(3) or found.group(2))) if found else None


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def cite_status(root: Path, file: str, line: int | None = None) -> str:
    """"ok", "escape" (outside the repository), or "missing" (no such regular file of at most 5 MB, or the line is past its end)."""
    try:
        target = safe_path(root, file)
    except (PathEscape, OSError, ValueError):
        return "escape"
    try:
        if not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
            return "missing"
        if line is None:
            return "ok"
        data = target.read_bytes()
    except OSError:
        return "missing"
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return "ok" if 1 <= line <= lines else "missing"


def check_item(item: dict, kind: str, source: Path | None, strict: bool = True) -> dict:
    """One review record, checked. `source` is the folder the citations point into; None means there is nothing to check against.

    Returns the record with `total` (the sum, by code), `verdict` (computed), `effective` (after the evidence checks), `evidence`,
    `low`, `low_reason`, `problems`, and flaws with their file and line split out.
    """
    rubric, problems = RUBRIC[kind], []
    scores = item.get("scores") if isinstance(item.get("scores"), dict) else {}
    total = 0
    for dimension, top in rubric.items():
        value = scores.get(dimension)
        if not _whole(value) or not 0 <= value <= top:
            problems.append(f"{dimension} must be a whole number from 0 to {top} (got {value if value is not None else 'nothing'})")
        else:
            total += value
    problems += [f"unknown dimension {name}" for name in scores if name not in rubric]
    claimed = item.get("total")
    if claimed != total:
        problems.append(f"total {claimed} does not equal the sum of the scores ({total}); the sum is used")
    computed = verdict_for(total)
    if item.get("verdict") != computed:
        problems.append(f"verdict {item.get('verdict')} does not follow the rule for {total} ({computed}); the rule is used")
    flaws = []
    for flaw in item.get("flaws") or []:
        cite = parse_cite(flaw.get("evidence"))
        if not cite or not str(flaw.get("fix", "")).strip():
            problems.append(f"flaw \"{flaw.get('dimension') or '?'}\" needs evidence as path:line and a fix")
        flaws.append({**flaw, "file": cite[0] if cite else "", "line": cite[1] if cite else None})
    if computed != "APPROVED" and not flaws:
        problems.append("a score below 100 must name each flaw with its evidence and fix")
    component = item.get("component") or {}
    reject = False
    if kind == "design" and (not component.get("file") or not _whole(component.get("line")) or component["line"] < 1):
        problems.append("the component under test (file, line, symbol) is missing")
        reject = True
    if kind == "code" and not item.get("file"):
        problems.append("the test file is missing")
        reject = True
    evidence, missing = "not-checked", []
    if source is not None and source.exists():
        cites: list[tuple[str, int | None]] = []
        if kind == "design" and component.get("file"):
            cites.append((component["file"], component.get("line") if _whole(component.get("line")) else None))
        if kind == "code" and item.get("file"):
            cites.append((item["file"], None))
        for flaw in flaws:
            cite = parse_cite(flaw["evidence"])
            if cite:
                cites += [(cite[0], cite[1]), (cite[0], cite[2])]
        escaped = False
        for file, line in cites:
            state = cite_status(source, file, line)
            escaped |= state == "escape"
            if state != "ok" and (label := f"{file}:{line}" if line else file) not in missing:
                missing.append(label)
        evidence = "verified" if not missing else "missing" if strict else "not-checked"
        if missing and strict:
            problems.append(("cited path is outside the repository: " if escaped else "cited evidence not found in the repository: ") + ", ".join(missing[:3]) + (f" (+{len(missing) - 3})" if len(missing) > 3 else ""))
    effective = "REJECT" if evidence == "missing" or reject else computed
    assertion = scores.get("assertion_integrity") if kind == "code" else None
    if effective == "REJECT":
        low_reason = "verdict REJECT"
    elif total < THRESHOLD:
        low_reason = f"total {total} is under {THRESHOLD}"
    elif _whole(assertion) and assertion < ASSERTION_FLOOR:
        low_reason = f"assertion integrity {assertion}/30 is under {ASSERTION_FLOOR}: the test may pass without proving the behaviour"
    else:
        low_reason = ""
    return {"tc_id": item.get("tc_id", ""), "kind": kind, "file": item.get("file", ""), "component": component or None, "scores": scores, "claimed_total": claimed, "total": total,
            "verdict": effective, "scored_verdict": computed, "evidence": evidence, "low": bool(low_reason), "low_reason": low_reason, "flaws": flaws, "problems": problems, "status": "reviewed"}


def not_run(tc_id: str, kind: str, reason: str) -> dict:
    """The honest result of a review that could not run: no score, never a pass."""
    return {"tc_id": tc_id, "kind": kind, "status": "NOT RUN", "verdict": "NOT RUN", "total": None, "evidence": "not-checked", "low": True, "low_reason": "review did not run", "flaws": [], "problems": [reason[:300]], "scores": {}}


def check_doc(review: dict, kind: str, source: Path | None, strict: bool = True) -> dict:
    """Checks every record of a review ({items}) and summarises it."""
    records = [check_item(item, kind, source, strict) for item in review.get("items", []) if item.get("tc_id")]
    return {"items": records, "summary": summarise(records)}
