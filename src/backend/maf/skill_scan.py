"""Static security scan of a skill folder: what it finds, file and line, and nothing graded.

Checks: SKILL.md present with frontmatter, prompt-injection phrases in Markdown, dangerous calls in Python scripts
(eval/exec/compile/__import__, os.system/popen/spawn, subprocess or asyncio with shell=True), hardcoded secrets, and
parent-directory paths in scripts. Scripts are parsed, never run.
ponytail: pattern lists, not a full taint analysis; NVIDIA SkillSpector is the deeper scanner (plan M3).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

INJECTION = [(re.compile(p, re.I), label) for p, label in (
    (r"ignore\s+(all\s+)?previous\s+instructions", "instruction override"),
    (r"system\s*override", "system override"),
    (r"disregard\s+(the\s+)?safety", "safety bypass"),
    (r"<\s*script[^>]*>", "HTML script tag"),
)]
SECRETS = [(re.compile(p), label) for p, label in (
    (r"sk-[A-Za-z0-9]{32,}", "OpenAI-style API key"),
    (r"gh[pousr]_[A-Za-z0-9]{36,}", "GitHub token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
)]
DANGEROUS_NAMES = {"eval", "exec", "compile", "__import__"}
DANGEROUS_OS = {"system", "popen", "spawnl", "spawnlp", "spawnv", "spawnvp"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".js", ".ts", ".sh", ".ps1"}


def _finding(check: str, severity: str, file: str, line: int | None, detail: str) -> dict:
    return {"check": check, "severity": severity, "file": file, "line": line, "detail": detail}


def _python(path: Path, rel: str) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
    except SyntaxError as exc:
        return [_finding("syntax", "high", rel, exc.lineno, f"does not parse: {exc.msg}")]
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in DANGEROUS_NAMES:
            found.append(_finding("code-execution", "critical", rel, node.lineno, f"calls {func.id}()"))
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "os" and func.attr in DANGEROUS_OS:
                found.append(_finding("shell", "critical", rel, node.lineno, f"calls os.{func.attr}()"))
            shell = any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords)
            if func.value.id in ("subprocess", "asyncio") and shell:
                found.append(_finding("shell", "critical", rel, node.lineno, f"calls {func.value.id}.{func.attr} with shell=True"))
    return found


def scan(skill_dir: Path) -> dict:
    """Findings for one skill folder. `checked` names every check that ran, so an empty list of findings means something."""
    findings: list[dict] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        findings.append(_finding("skill-md", "critical", "SKILL.md", None, "SKILL.md is missing"))
    elif not skill_md.read_text(encoding="utf-8", errors="replace").startswith("---"):
        findings.append(_finding("frontmatter", "high", "SKILL.md", 1, "SKILL.md does not start with YAML frontmatter"))
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES):
        rel = path.relative_to(skill_dir).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for number, line in enumerate(lines, 1):
            for pattern, label in SECRETS:
                if pattern.search(line):
                    findings.append(_finding("secret", "critical", rel, number, f"looks like a {label}"))
            if path.suffix.lower() == ".md":
                for pattern, label in INJECTION:
                    if pattern.search(line):
                        findings.append(_finding("prompt-injection", "critical", rel, number, f"phrase: {label}"))
        if path.suffix.lower() == ".py":
            findings.extend(_python(path, rel))
            findings.extend(_finding("path", "medium", rel, n, "refers to a parent directory (../)")
                            for n, line in enumerate(lines, 1) if "../" in line or "..\\" in line)
    return {"skill": skill_dir.name, "findings": findings,
            "checked": ["SKILL.md and frontmatter", "prompt-injection phrases in Markdown", "dangerous calls in Python",
                        "hardcoded secrets", "parent-directory paths in Python"]}
