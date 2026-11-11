"""Static checks on generated Python test code."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from backend.qe.emit.inventory import ALIASES, _normal
from backend.qe.emit.project import Project
from backend.qe.emit.sigs import RAISES, Sig, _class_sig, _function_sig, _method_sig, call_problem


def _guarded_imports(tree: ast.Module) -> set[int]:
    """Imports inside `try` with an ImportError handler: the author expected them to fail."""
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(h.type is None or "ImportError" in ast.unparse(h.type) or "ModuleNotFoundError" in ast.unparse(h.type) or "Exception" in ast.unparse(h.type) for h in node.handlers):
            guarded |= {id(n) for stmt in node.body for n in ast.walk(stmt)}
    return guarded


def _chain(node: ast.AST) -> list[str] | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return [node.id, *reversed(parts)]
    return None


def check_python(worktree: Path, path: str, code: str, env: dict | None = None, declared: set[str] | frozenset = frozenset()) -> list[str]:
    """Findings for one generated Python test. Each says where, what, and the real signature when there is one."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # execution.syntax_error reports this
    project = Project(worktree, (worktree / path).parent)
    stdlib = env["stdlib"] if env else set(sys.stdlib_module_names)
    guarded = _guarded_imports(tree)
    findings: list[str] = []
    classes: dict[str, tuple[ast.ClassDef, Path]] = {}
    functions: dict[str, tuple[ast.AST, Path]] = {}
    modules: dict[str, str] = {}  # local name to a dotted local module
    third: dict[str, str] = {}  # local name to the dotted name it has in a third-party package

    for node in ast.walk(tree):
        if id(node) in guarded:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if project.is_local(top):
                    if project.module(alias.name) is None:
                        findings.append(f"{path}:{node.lineno}: module {alias.name} does not exist in this repository")
                    else:
                        modules[alias.asname or top] = alias.name if alias.asname else top
                elif top not in stdlib:
                    third[alias.asname or top] = alias.name if alias.asname else top
                    findings += _third_party(path, node.lineno, top, env, declared)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            top = node.module.split(".")[0]
            if not project.is_local(top):
                if top not in stdlib:
                    findings += _third_party(path, node.lineno, top, env, declared)
                    for alias in node.names:
                        third[alias.asname or alias.name] = f"{node.module}.{alias.name}"
                continue
            target = project.module(node.module)
            if target is None:
                findings.append(f"{path}:{node.lineno}: module {node.module} does not exist in this repository")
                continue
            available = project.names(target)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if available is not None and alias.name not in available:
                    findings.append(f"{path}:{node.lineno}: {node.module} has no name {alias.name!r}" + (f". It has: {', '.join(sorted(n for n in available if not n.startswith('_'))[:30])}" if available else ""))
                    continue
                local = alias.asname or alias.name
                if hit := project.find(target, alias.name):
                    (classes if isinstance(hit[0], ast.ClassDef) else functions)[local] = hit  # type: ignore[assignment]
                elif project.module(f"{node.module}.{alias.name}") is not None:
                    modules[local] = f"{node.module}.{alias.name}"

    instances: dict[str, ast.ClassDef | None] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id in classes:
            made, name = classes[node.value.func.id][0], node.targets[0].id
            instances[name] = made if instances.get(name, made) is made else None  # a name assigned two different classes is not tracked

    def resolve(call: ast.Call) -> Sig | None:
        chain = _chain(call.func)
        if not chain:
            return None
        if len(chain) == 1:
            if chain[0] in functions:
                node = functions[chain[0]][0]
                return _function_sig(node) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None
            return _class_sig(classes[chain[0]][0]) if chain[0] in classes else None
        if chain[0] in classes and len(chain) == 2:
            return _method_sig(classes[chain[0]][0], chain[1])
        if chain[0] in instances and instances[chain[0]] is not None and len(chain) == 2:
            return _method_sig(instances[chain[0]], chain[1])
        if chain[0] in modules:
            dotted = [*modules[chain[0]].split("."), *chain[1:]]
            for cut in range(len(dotted) - 1, 0, -1):  # the longest module prefix that exists, then the function or class in it
                target = project.module(".".join(dotted[:cut]))
                if target is None or not target.is_file():
                    continue
                hit = project.find(target, dotted[cut])
                rest = dotted[cut + 1:]
                if hit is None:
                    return None
                if isinstance(hit[0], ast.ClassDef):
                    return _class_sig(hit[0]) if not rest else _method_sig(hit[0], rest[0]) if len(rest) == 1 else None
                return _function_sig(hit[0]) if not rest and isinstance(hit[0], (ast.FunctionDef, ast.AsyncFunctionDef)) else None
        return None

    httpx_version = tuple(int(x) for x in re.findall(r"\d+", (env or {}).get("versions", {}).get("httpx", ""))[:2])

    class Calls(ast.NodeVisitor):
        def visit_With(self, node):
            if any(isinstance(i.context_expr, ast.Call) and (c := _chain(i.context_expr.func)) and c[-1] in RAISES for i in node.items):
                return  # a test may call a function wrongly on purpose to see it raise
            self.generic_visit(node)

        def visit_Try(self, node):
            catches = any(h.type is not None and "TypeError" in ast.unparse(h.type) for h in node.handlers)
            for block in ([] if catches else node.body, node.orelse, node.finalbody, *(h.body for h in node.handlers)):
                for stmt in block:
                    self.visit(stmt)

        def visit_Call(self, node):
            chain = _chain(node.func)
            if chain and chain[0] in third and httpx_version >= (0, 28):
                full = ".".join([third[chain[0]], *chain[1:]])
                if full in {"httpx.AsyncClient", "httpx.Client"} and any(k.arg == "app" for k in node.keywords):
                    findings.append(f"{path}:{node.lineno}: {full}(app=...) was removed in httpx 0.28 and this environment has {'.'.join(map(str, httpx_version))}. Use transport=httpx.ASGITransport(app=app) for an ASGI app or httpx.WSGITransport(app=app) for a WSGI app, with base_url='http://test'")
            if (sig := resolve(node)) and (problem := call_problem(node, sig)):
                findings.append(f"{path}:{node.lineno}: the call {ast.unparse(node.func)}(...) {problem}. Real signature: {sig.text}")
            self.generic_visit(node)

    Calls().visit(tree)
    return findings


def _third_party(path: str, line: int, top: str, env: dict | None, declared: set[str] | frozenset) -> list[str]:
    if env is None or top in env["modules"] or _normal(top) in declared or ALIASES.get(top.lower(), "") in declared:
        return []  # without an inventory nothing can be said
    return [f"{path}:{line}: the package {top!r} is not installed in the test environment. Use only the standard library, pytest, and what the repository's code already imports, and import the repository's real module under test instead of writing your own"]
