"""Checks on generated test code: syntax, assertions, imports."""
from __future__ import annotations

import ast
import re
from pathlib import Path


def syntax_error(path: str, code: str) -> str | None:
    if path.endswith(".py"):
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return f"{path}:{exc.lineno}: {exc.msg}"
    return None


ASSERTION = re.compile(r"\bassert\b|\bexpect\(|\.assert\w*\(|\bshould\b")


WEAKENING = re.compile(r"assert\s+True\b|expect\(\s*true\s*\)|pytest\.skip|\.skip\(|xfail|@Disabled|\.only\(")


def assertions_preserved(old: str, new: str) -> tuple[bool, str]:
    """Port of apply-healing.ts: healing may repair selectors or fixtures, never weaken an assertion."""
    before = [l.strip() for l in old.splitlines() if ASSERTION.search(l)]
    after = [l.strip() for l in new.splitlines() if ASSERTION.search(l)]
    if WEAKENING.search(new) and not WEAKENING.search(old):
        return False, "Patch introduces a skip or a tautological assertion"
    if len(after) < len(before):
        return False, f"Patch removes assertions ({len(before)} to {len(after)})"
    if [l for l in before if l not in after]:
        return False, "Patch changes an existing assertion"
    return True, ""


def _module_names(path: Path) -> set[str] | None:
    """Names a Python module defines at top level. None when it cannot be known, such as with star imports."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    return None
                names.add((alias.asname or alias.name).split(".")[0])
    return None if "__getattr__" in names else names


def invalid_test_code(worktree: Path, path: str, code: str, async_ok: bool = False) -> list[str]:
    """Generated tests must import names that exist and use only plugins the repository has. Agents invent both.

    `async_ok` is true when the platform will make pytest-asyncio available (it is installed, or the run installs dependencies)."""
    if not path.endswith(".py"):
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # syntax_error reports this
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level or not node.module:
            continue
        base = worktree.joinpath(*node.module.split("."))
        module = base.with_suffix(".py") if base.with_suffix(".py").is_file() else base / "__init__.py"
        if not module.is_file():
            # Check if module exists in known subroots like backend, src, app, modules
            for sub in ("backend", "src", "server", "app"):
                cand = (worktree / sub).joinpath(*node.module.split("."))
                cand_mod = cand.with_suffix(".py") if cand.with_suffix(".py").is_file() else cand / "__init__.py"
                if cand_mod.is_file():
                    base = cand
                    module = cand_mod
                    break
            else:
                top = node.module.split(".")[0]
                has_top = (worktree / top).exists() or any((worktree / sub / top).exists() for sub in ("backend", "src", "server", "app"))
                if has_top:
                    issues.append(f"{path}: module {node.module} does not exist")
                continue
        available = _module_names(module)
        submodules = {p.stem for p in base.glob("*.py")} | {p.name for p in base.iterdir() if p.is_dir()} if base.is_dir() else set()
        missing = [a.name for a in node.names if available is not None and a.name != "*" and a.name not in available and a.name not in submodules]
        if missing:
            issues.append(f"{path}: {node.module} has no {', '.join(missing)}")
    if not async_ok and re.search(r"pytest\.mark\.asyncio|^\s*async def test_", code, re.M):
        manifests = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in worktree.glob("*") if p.name.startswith(("requirements", "pyproject", "setup")) and p.is_file())
        if "pytest-asyncio" not in manifests and "pytest_asyncio" not in manifests:
            issues.append(f"{path}: this repository does not have pytest-asyncio. Write a normal test and call asyncio.run() if needed")
    return issues
