"""A generated test must exercise the repository's code, never a copy or a stub of its subject that the test defines itself."""
from __future__ import annotations

import ast
from pathlib import Path

from backend.core.security import PathEscape, safe_path
from backend.qe.emit.project import Project

# ponytail: a browser or HTTP test reaches the product over the wire without importing it. The usual clients only.
CLIENTS = {"playwright", "selenium", "requests", "httpx", "urllib", "aiohttp", "http"}
_PATCHERS = {"patch", "setattr", "object"}  # mock.patch("m.f"), monkeypatch.setattr(m, "f", ...), mock.patch.object(m, "f")


def _defined(tree: ast.Module) -> dict[str, int]:
    """Functions, classes and lambdas the file defines at the top level, other than tests and fixtures."""
    found: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith(("test", "Test")) and not any("fixture" in ast.unparse(d) for d in node.decorator_list):
                found[node.name] = node.lineno
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Lambda):
            found |= {t.id: node.lineno for t in node.targets if isinstance(t, ast.Name)}
    return found


def _imports(tree: ast.Module, project: Project) -> tuple[dict[str, set[str] | None], bool]:
    """Repository modules the file imports, each with the names it offers (None when unknown), and whether it imports a browser or HTTP client."""
    local: dict[str, set[str] | None] = {}
    client = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                client |= alias.name.split(".")[0] in CLIENTS
                if project.is_local(alias.name.split(".")[0]) and (target := project.module(alias.name)):
                    local[alias.asname or alias.name] = project.names(target)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            client |= node.module.split(".")[0] in CLIENTS
            if project.is_local(node.module.split(".")[0]) and (target := project.module(node.module)):
                local[node.module] = (project.names(target) or set()) | {a.asname or a.name for a in node.names}
    return local, client


def _patched(tree: ast.Module, local: dict) -> set[str]:
    """Names of repository modules that the file replaces with a mock or monkeypatch."""
    names = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and node.args and getattr(node.func, "attr", getattr(node.func, "id", "")) in _PATCHERS):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str) and "." in first.value and first.value.rsplit(".", 1)[0] in local:
            names.add(first.value.rsplit(".", 1)[1])
        elif isinstance(first, ast.Name) and first.id in local and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
            names.add(str(node.args[1].value))
    return names


def own_subject(worktree: Path, path: str, code: str) -> list[str]:
    """Findings for a Python test that defines or stubs its own subject instead of exercising the repository's code."""
    if not path.endswith(".py"):
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # execution.syntax_error reports this
    local, client = _imports(tree, Project(worktree, (worktree / path).parent))
    offered = set().union(*(names or set() for names in local.values()))
    defined = _defined(tree)
    findings = [f"{path}:{line}: defines {name} itself, which replaces the repository's real {name}. Import the repository's real one and test that" for name, line in defined.items() if name in offered]
    if defined and not local and not client:
        name, line = next(iter(defined.items()))
        findings.append(f"{path}:{line}: defines {name} itself and imports no code from the repository, so it would test its own copy. Import the repository's real module under test; "
                        "if it does not exist yet, import it anyway so the test fails")
    called = {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    findings += [f"{path}: replaces {name} from the repository with a stub and then calls it, so it checks the stub. Stub only external services" for name in sorted(_patched(tree, local) & called)]
    return findings


def exercises_repository(worktree: Path, path: str) -> bool:
    """Whether a test file on disk reaches the product: it imports repository code or a browser or HTTP client, and does not define or stub its subject.
    ponytail: only Python is read; a test in another language counts as reaching the product."""
    if not path.endswith(".py"):
        return True
    try:
        code = safe_path(worktree, path).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(code)
    except (OSError, PathEscape, SyntaxError, ValueError):
        return False
    local, client = _imports(tree, Project(worktree, (worktree / path).parent))
    return bool(local or client) and not own_subject(worktree, path, code)
