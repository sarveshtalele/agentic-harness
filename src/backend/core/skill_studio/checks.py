"""The checks every skill passes before it is published: generated, uploaded, or run through the evaluator script.

Each check is {check, passed, detail}. Nothing is graded beyond passed and total. Python is parsed, never executed.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import yaml

NAME_RULE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BODY_LINES = 500


def frontmatter(text: str) -> tuple[dict | None, str]:
    """The YAML between the opening --- lines, and the body after it. None when there is none or it does not parse."""
    if not text.startswith("---") or "\n---" not in text[3:]:
        return None, text
    head, body = text[3:].split("\n---", 1)
    try:
        front = yaml.safe_load(head)
    except yaml.YAMLError:
        return None, body
    return (front if isinstance(front, dict) else None), body.split("\n", 1)[1] if "\n" in body else ""


def maf_loads(skill_dir: Path) -> tuple[bool, str]:
    """MAF's own FileSkillsSource decides whether the folder is a skill."""
    from agent_framework import FileSkillsSource, SkillsSourceContext

    from backend.core.skills import _run

    loaded = {Path(s.path).resolve() for s in _run(FileSkillsSource([skill_dir.parent]).get_skills(SkillsSourceContext(agent=None)))}
    ok = skill_dir.resolve() in loaded
    return ok, "MAF FileSkillsSource loaded it" if ok else "MAF FileSkillsSource did not load it"


def run(skill_dir: Path) -> list[dict]:
    checks: list[dict] = []

    def check(label: str, passed: bool, detail: str) -> None:
        checks.append({"check": label, "passed": bool(passed), "detail": detail})

    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8", errors="replace") if skill_md.is_file() else ""
    front, body = frontmatter(text)
    check("frontmatter", front is not None, "YAML frontmatter between --- lines" if front is not None else "SKILL.md is missing or has no readable YAML frontmatter")
    front = front or {}
    name, description = str(front.get("name", "")), str(front.get("description", "")).strip()
    check("name format", bool(NAME_RULE.fullmatch(name)) and len(name) <= 64, f"name {name!r}: lowercase letters, digits and single hyphens, at most 64")
    check("name matches folder", name == skill_dir.name, f"name {name!r}, folder {skill_dir.name!r}")
    check("description", 0 < len(description) <= 1024, f"{len(description)} characters (1 to 1024)")
    lines = len(body.splitlines())
    check("body length", lines <= BODY_LINES, f"{lines} lines (at most {BODY_LINES}; move detail into references/)")
    check("MAF loads it", *maf_loads(skill_dir))
    for script in sorted(p for p in skill_dir.rglob("*.py") if p.is_file()):
        rel = script.relative_to(skill_dir).as_posix()
        try:
            ast.parse(script.read_text(encoding="utf-8", errors="replace"), filename=rel)
            check(f"{rel} parses", True, "Python syntax is valid (parsed, not executed)")
        except SyntaxError as exc:
            check(f"{rel} parses", False, f"line {exc.lineno}: {exc.msg}")
    from backend.maf.skill_scan import scan  # late: maf imports core

    findings = scan(skill_dir)["findings"]
    check("security scan", not findings, "no findings" if not findings else "; ".join(f"{f['file']}:{f['line']} {f['check']}: {f['detail']}" for f in findings[:10]))
    return checks


def summary(checks: list[dict]) -> dict:
    passed = sum(c["passed"] for c in checks)
    return {"passed": passed, "total": len(checks), "all_passed": passed == len(checks)}


def read_files(skill_dir: Path) -> list[dict]:
    """Every file of a skill folder as {path, content}, sorted by path. Skill content is text."""
    return [{"path": p.relative_to(skill_dir).as_posix(), "content": p.read_text(encoding="utf-8", errors="replace")}
            for p in sorted(skill_dir.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


def digest(files: list[dict]) -> str:
    """SHA-256 over sorted (path, content), so the same files always give the same hash."""
    pairs = sorted((f["path"], f["content"]) for f in files)
    return hashlib.sha256(json.dumps(pairs, ensure_ascii=False).encode()).hexdigest()
