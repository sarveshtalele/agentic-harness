"""Parsed project index and real signatures for prompts."""
from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path
from backend.qe.emit.inventory import SIGNATURE_BUDGET
from backend.qe.emit.sigs import _class_sig, _decorator_names, _shallow, _sig, _transparent


@lru_cache(maxsize=512)
def _parse_cached(path: str, stamp: tuple) -> ast.Module | None:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return None


def _parsed(path: Path) -> ast.Module | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return _parse_cached(str(path), (stat.st_mtime_ns, stat.st_size))


class Project:
    """Where local modules live: the repository root, `src/`, `backend/`, and the folder of the test itself (pytest puts that on the path)."""

    def __init__(self, worktree: Path, test_dir: Path):
        roots = [worktree, worktree / "src", test_dir]
        for sub in ("backend", "server", "app", "lib", "packages", "modules", "core"):
            cand = worktree / sub
            if cand.is_dir() and cand not in roots:
                roots.append(cand)
        self.roots = roots

    @staticmethod
    def locate(base: Path) -> Path | None:
        if base.with_suffix(".py").is_file():
            return base.with_suffix(".py")
        if (base / "__init__.py").is_file():
            return base / "__init__.py"
        return base if base.is_dir() else None

    def module(self, dotted: str) -> Path | None:
        for root in self.roots:
            if found := self.locate(root.joinpath(*dotted.split("."))):
                return found
        # Common alias fallback: backend.main -> backend.app.main
        if dotted == "backend.main":
            return self.module("backend.app.main")
        return None

    def is_local(self, top: str) -> bool:
        return any((root / f"{top}.py").is_file() or (root / top).is_dir() for root in self.roots)

    def resolve_from(self, path: Path, node: ast.ImportFrom) -> Path | None:
        if node.level:
            base = path.parent
            for _ in range(node.level - 1):
                base = base.parent
            return self.locate(base.joinpath(*node.module.split("."))) if node.module else self.locate(base)
        return self.module(node.module) if node.module else None

    def names(self, path: Path, depth: int = 0) -> set[str] | None:
        """Names a module offers. None when they cannot be known (a module `__getattr__`, a star import that cannot be followed)."""
        if path.is_dir():
            return {p.stem for p in path.glob("*.py")} | {p.name for p in path.iterdir() if p.is_dir()}
        tree = _parsed(path)
        if tree is None:
            return None
        names: set[str] = set()
        for node in ast.walk(tree):  # deliberately generous: a name defined anywhere counts, so a real name is never reported missing
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                names.add(node.id)
            elif isinstance(node, ast.Import):
                names.update((a.asname or a.name).split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        names.add(alias.asname or alias.name)
                        continue
                    target = self.resolve_from(path, node)
                    sub = self.names(target, depth + 1) if target and depth < 4 else None
                    if sub is None:
                        return None
                    names |= sub
        if "__getattr__" in names:
            return None
        if path.name == "__init__.py":
            names |= {p.stem for p in path.parent.glob("*.py")} | {p.name for p in path.parent.iterdir() if p.is_dir()}
        return names

    def find(self, path: Path, name: str, depth: int = 0) -> tuple[ast.AST, Path] | None:
        """The function or class `name` of a module, following re-exports."""
        tree = _parsed(path) if path.is_file() else None
        if tree is None or depth > 6:
            return None
        found = None
        for node in _shallow(tree.body):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                found = node
        if found is not None:
            return found, path
        for node in _shallow(tree.body):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = self.resolve_from(path, node)
            if target is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    if hit := self.find(target, name, depth + 1):
                        return hit
                elif (alias.asname or alias.name) == name:
                    return self.find(target, alias.name, depth + 1)
        return None


def signatures(worktree: Path, paths: list[str], budget: int = SIGNATURE_BUDGET) -> str:
    """The real signatures of the public functions and classes in the files under test, so a test is written against them. Bounded by `budget`."""
    lines, used = [], 0
    for rel in paths:
        file = worktree / rel
        tree = _parsed(file) if rel.endswith(".py") and file.is_file() else None
        if tree is None:
            continue
        dotted = ".".join(Path(rel[4:] if rel.startswith("src/") else rel).with_suffix("").parts).removesuffix(".__init__")
        entries = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_") and _transparent(node):
                entries.append(("async " if isinstance(node, ast.AsyncFunctionDef) else "") + _sig(node.name, node.args).text)
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                sig = _class_sig(node)
                methods = [("async " if isinstance(m, ast.AsyncFunctionDef) else "") + _sig(m.name, m.args, drop="staticmethod" not in _decorator_names(m)).text
                           for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_") and _transparent(m)]
                entries.append(f"class {sig.text if sig else node.name + '(...)'}" + (f" with methods {'; '.join(methods[:12])}" if methods else ""))
        if not entries:
            continue
        block = f"from {dotted} import ...  ({rel})\n" + "\n".join(f"  {e}" for e in entries) + "\n"
        if used + len(block) > budget:
            break
        lines.append(block)
        used += len(block)
    return ("REAL SIGNATURES. Call these exactly, with these parameter names:\n" + "\n".join(lines)) if lines else ""
