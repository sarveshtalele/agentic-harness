"""The generated suite as typed data, and the code checks that refuse a generated test file."""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from backend.qe import execution
from backend.qe.emit.subject import own_subject

# ponytail: the case fields a test author reaches for; fixtures.json holds none of them, so reading one is the KeyError seen in a real run
_NOT_FIXTURE_KEYS = re.compile(r"""(?:\[|\.get\()\s*["'](test_data|expected_result|precondition|steps|scenario|oracle)["']""")


class GeneratedFile(BaseModel):
    path: str
    case_ids: list[str] = Field(min_length=1)
    content: str


class GeneratedSuite(BaseModel):
    framework: str
    files: list[GeneratedFile] = Field(min_length=1)


def _clean_code(code: str) -> str:
    text = (code or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
    return text


def _generated_file_problems(item: GeneratedFile, known: set[str], worktree: Path, async_ok: bool = False) -> list[str]:
    item.content = _clean_code(item.content)
    errors = list(execution.invalid_test_code(worktree, item.path, item.content, async_ok))
    if not set(item.case_ids) <= known:
        errors.append(f"{item.path}: unknown case ids")
    if issue := execution.syntax_error(item.path, item.content):
        errors.append(issue)
    if re.search(r"assert\s+True\b|expect\(\s*true\s*\)\.toBe\(\s*true\s*\)", item.content):
        errors.append(f"{item.path}: tautological assertion")
    if placeholder := re.search(r"^\s*(pass|\.\.\.)\s*$|\bTODO\b", item.content, re.M):
        errors.append(f"{item.path}: line {item.content.count(chr(10), 0, placeholder.start()) + 1} has placeholder code ({placeholder.group(0).strip()}). Remove it and write real code. Do not use pass, an ellipsis, or the word TODO anywhere in the file")
    if "CASE_ID" not in item.content.splitlines()[0]:
        errors.append(f"{item.path}: first line must be a CASE_ID comment")
    if len(item.case_ids) != 1:
        errors.append(f"{item.path}: one case per file")
    errors += own_subject(worktree, item.path, item.content)
    if "fixtures.json" in item.content and (key := _NOT_FIXTURE_KEYS.search(item.content)):
        errors.append(f"{item.path}: reads the key {key.group(1)!r}, which fixtures.json does not have. Under \"cases\" each case id has only \"data\" (its test data as text) "
                      "and \"uses\" (names of the shared datasets under \"datasets\")")
    if not item.path.replace("\\", "/").startswith("tests/agentic_qe/"):
        errors.append(f"{item.path}: must live under tests/agentic_qe/")
    return errors
