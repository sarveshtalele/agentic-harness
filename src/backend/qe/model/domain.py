"""Checks of designed cases against what their requirement states: its input type and its error behaviour."""
from __future__ import annotations

import ast
import json
import re

ACCEPTS = {"string": {"string"}, "number": {"number", "integer"}, "integer": {"integer"}, "boolean": {"boolean"}, "list": {"list"}, "object": {"object"}}
ALIASES = {"str": "string", "text": "string", "markdown": "string", "int": "integer", "float": "number", "decimal": "number", "bool": "boolean",
           "array": "list", "tuple": "list", "dict": "object", "dictionary": "object", "json": "object", "map": "object"}
_ERROR_IN_QUOTE = re.compile(r"\b(raise|throw|throws|abort)\b|HTTPException|status_code\s*=\s*[45]\d\d")
_DESCRIBED = re.compile(r"^(?:an?|the)\s+(?:python\s+|javascript\s+)?(list|array|tuple|dict(?:ionary)?|object|integer|int|float|number|boolean)\b", re.I)


def input_type(value) -> str:
    """The canonical name of a stated input type, or "" when none or an unknown one is stated."""
    text = str(value or "").strip().lower()
    text = ALIASES.get(text, text)
    return text if text in ACCEPTS else ""


def states_error(requirement: dict) -> bool:
    """ponytail: the analyst's error_behaviour, or a raise or throw on the verified quote line. An error path elsewhere in the code is not seen."""
    return bool(str(requirement.get("error_behaviour") or "").strip()) or bool(_ERROR_IN_QUOTE.search(requirement.get("quote") or ""))


def _kind(value) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (list, tuple, set)):
        return "list"
    return {int: "integer", float: "number", str: "string", dict: "object"}.get(type(value), "string")


def data_kind(text: str) -> str:
    """What kind of value test data names: "42" and "input = 123 (integer)" are integers, "None" and "null" are none, "A Python list ..." is a list. Other text is a string."""
    raw = re.sub(r"\s*\((?:an?\s+)?\w+\)\s*$", "", re.sub(r"^\s*\w+\s*=\s*", "", text.strip()))
    if described := _DESCRIBED.match(raw):
        return input_type(described.group(1)) or ALIASES.get(described.group(1).lower(), "string")
    for parse in (ast.literal_eval, json.loads):
        try:
            return _kind(parse(raw))
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            continue
    return "string"


def _fits(kind: str, wanted: str, text: str) -> bool:
    if kind in ACCEPTS[wanted]:
        return True
    if kind == "list" and wanted in ("number", "integer"):  # "2, 3": several arguments of the stated type
        return all(data_kind(part) in ACCEPTS[wanted] for part in text.split(","))
    return False


def case_problems(requirements: list[dict], cases: list[dict]) -> list[tuple[dict, str]]:
    """Each case whose test data is of another type than its requirement's stated input, with why. Another type is allowed only
    in an Exception case for a requirement that states error behaviour. A requirement that states no input type is not checked."""
    by_id = {r["id"]: r for r in requirements}
    found = []
    for case in cases:
        requirement = by_id.get(case["requirement_id"], {})
        wanted, data = input_type(requirement.get("input_type")), str(case.get("test_data") or "").strip()
        if not wanted or not data or (case.get("type") == "Exception" and states_error(requirement)):
            continue
        if not _fits(kind := data_kind(data), wanted, data):
            found.append((case, f"{case['requirement_id']}: case '{case['scenario'][:60]}' has test data {data[:60]!r}, a {kind}, but the requirement states its input type as {wanted}. "
                                "Use a value of that type, or state the error behaviour in the requirement first"))
    return found
