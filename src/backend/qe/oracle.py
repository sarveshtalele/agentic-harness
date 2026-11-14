"""V2 (design): a case's expected result must be derivable from its requirement's quote, statement or the code near the cited line.

Concrete values in expected_result (quoted texts, exception names, status codes, numbers) that appear in none of them are invented
by the model, so the case is refused with a fix message. Code decides; no model is asked.
"""
from __future__ import annotations

import builtins
import re
from pathlib import Path

from backend.core.security import safe_path
from backend.repos import scan

QUOTED = re.compile(r"""(?<![\w])(['"`])(.{2,80}?)\1(?!\w)""")
EXCEPTION = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Error|Exception))\b")
STATUS = re.compile(r"(?i)\b(?:status(?: code)?|http)\s*:?\s*(\d{3})\b")
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w])")
COMPUTED = {"derived", "metamorphic"}  # a computed result (2 + 3 = 5) need not appear as text; stated values still must
TRIVIAL = {"0", "1", "-1", "200"}  # a count of none or one, and the default success status, are not inventions


def code_near(root: Path | None, requirement: dict, radius: int = 40) -> str:
    """The raw source lines within `radius` of the requirement's cited line, or "" when there is no repository or citation."""
    if not root or not requirement.get("file"):
        return ""
    try:
        lines = scan._read(safe_path(root, requirement["file"])).splitlines()
    except (ValueError, OSError):
        return ""
    line = int(requirement.get("line") or 1)
    return "\n".join(lines[max(line - radius - 1, 0) : line + radius])


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def invented_values(case: dict, requirement: dict, code: str) -> list[str]:
    """The concrete values of the case's expected result that its sources do not contain. Empty when the requirement has no quote (nothing to derive from).

    ponytail: textual match only; a percentage written as 5% for a code constant 0.05 is refused and the redesign states the value the code shows.
    """
    if not requirement.get("quote"):
        return []
    expected = case.get("expected_result", "")
    source = _norm(" ".join([requirement["quote"], requirement.get("statement", ""), code, case.get("test_data", ""), case.get("precondition", ""), " ".join(case.get("steps", []))]))
    computed = case.get("oracle") in COMPUTED
    found = [m.group(2) for m in QUOTED.finditer(expected)]
    rest = QUOTED.sub(" ", expected)
    found += [n for n in EXCEPTION.findall(rest) if not (computed and hasattr(builtins, n))]
    found += [c for c in STATUS.findall(rest) if c not in TRIVIAL]
    if not computed:
        found += [n for n in NUMBER.findall(STATUS.sub(" ", rest)) if n not in TRIVIAL]
    missing = []
    for value in dict.fromkeys(found):
        if not re.search(rf"(?<![\w.]){re.escape(_norm(value))}(?![\w])" if value[:1].isalnum() else re.escape(_norm(value)), source):
            missing.append(value)
    return missing


def problems(cases: list[dict], requirements: list[dict], root: Path | None) -> dict[str, str]:
    """{case id: fix message} for every case whose expected result holds a value found nowhere in its sources."""
    by_id = {r["id"]: r for r in requirements}
    found = {}
    for case in cases:
        requirement = by_id.get(case["requirement_id"], {})
        if values := invented_values(case, requirement, code_near(root, requirement)):
            where = f"{requirement.get('file')}:{requirement.get('line')}" if requirement.get("file") else "the requirement"
            found[case["id"]] = (f"the expected result names {', '.join(repr(v) for v in values)}, which appears in neither the requirement's quote nor the code near {where}. "
                                 "Use only values the quote or the code states; for a computed result, set the oracle to derived and show the inputs")
    return found
