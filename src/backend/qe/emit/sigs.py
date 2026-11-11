"""Function and class signatures and call checking."""
from __future__ import annotations

import ast
from dataclasses import dataclass


PASS_THROUGH = {"staticmethod", "classmethod", "abstractmethod", "lru_cache", "cache", "override", "final", "overload"}  # decorators that keep a function's signature


RAISES = {"raises", "assertRaises", "assertRaisesRegex", "warns", "assertWarns"}


@dataclass
class Sig:
    name: str
    pos: list[str]  # positional parameters, positional-only first, `self` already dropped for methods
    posonly: int
    defaults: set[str]
    kwonly: list[str]
    kw_required: set[str]
    vararg: bool
    kwarg: bool
    text: str


def _sig(name: str, a: ast.arguments, drop: bool = False) -> Sig:
    posonly = [x.arg for x in a.posonlyargs]
    pos = posonly + [x.arg for x in a.args]
    nodes: list = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    if drop and pos:
        pos, nodes, posonly = pos[1:], nodes[1:], posonly[1:]
    parts = []
    for i, (n, d) in enumerate(zip(pos, nodes)):
        parts.append(n if d is None else f"{n}={ast.unparse(d)}")
        if posonly and i == len(posonly) - 1:
            parts.append("/")
    kwonly = [x.arg for x in a.kwonlyargs]
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    elif kwonly:
        parts.append("*")
    for n, d in zip(kwonly, a.kw_defaults):
        parts.append(n if d is None else f"{n}={ast.unparse(d)}")
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return Sig(name, pos, len(posonly), {n for n, d in zip(pos, nodes) if d is not None}, kwonly, {n for n, d in zip(kwonly, a.kw_defaults) if d is None}, bool(a.vararg), bool(a.kwarg), f"{name}({', '.join(parts)})")


def _decorator_names(node) -> list[str]:
    names = []
    for d in node.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        names.append(target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "?"))
    return names


def _transparent(node) -> bool:
    return all(n in PASS_THROUGH for n in _decorator_names(node))


def _function_sig(node: ast.FunctionDef | ast.AsyncFunctionDef, drop: bool = False) -> Sig | None:
    return _sig(node.name, node.args, drop) if _transparent(node) else None


def _class_sig(cls: ast.ClassDef) -> Sig | None:
    body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if any(n.name == "__new__" for n in body) or cls.keywords:
        return None
    init = next((n for n in body if n.name == "__init__"), None)
    if init:
        return _sig(cls.name, init.args, drop=True) if _transparent(init) else None
    decorators = _decorator_names(cls)
    if decorators == ["dataclass"] and not cls.bases and not any(isinstance(d, ast.Call) and d.keywords for d in cls.decorator_list):
        fields = [n for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and "ClassVar" not in ast.unparse(n.annotation)
                  and not (isinstance(n.value, ast.Call) and any(k.arg == "init" for k in n.value.keywords))]
        text = ", ".join(f.target.id if f.value is None else f"{f.target.id}=..." for f in fields)
        return Sig(cls.name, [f.target.id for f in fields], 0, {f.target.id for f in fields if f.value is not None}, [], set(), False, False, f"{cls.name}({text})")
    if not cls.bases and not decorators:
        return Sig(cls.name, [], 0, set(), [], set(), False, False, f"{cls.name}()")  # a plain class with no __init__ takes no arguments
    return None


def _method_sig(cls: ast.ClassDef, name: str) -> Sig | None:
    method = next((n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
    if method is None or not _transparent(method):
        return None
    return _sig(f"{cls.name}.{name}", method.args, drop="staticmethod" not in _decorator_names(method))


def call_problem(call: ast.Call, sig: Sig) -> str | None:
    """What is wrong with this call against the signature, or None when it fits or cannot be known."""
    starred = any(isinstance(a, ast.Starred) for a in call.args)
    spread = any(k.arg is None for k in call.keywords)
    given = len(call.args)
    names = [k.arg for k in call.keywords if k.arg]
    if not starred and not sig.vararg and given > len(sig.pos):
        return f"passes {given} positional arguments but it accepts {len(sig.pos)}"
    if not sig.kwarg:
        allowed = set(sig.pos[sig.posonly:]) | set(sig.kwonly)
        if bad := [n for n in names if n not in allowed]:
            return f"passes the keyword argument {', '.join(repr(n) for n in bad)}, which it does not accept"
    if not starred and (twice := [n for n in names if n in sig.pos[:given] and sig.pos.index(n) >= sig.posonly]):
        return f"gives {twice[0]!r} twice, by position and by keyword"
    if not starred and not spread:
        missing = [n for i, n in enumerate(sig.pos) if n not in sig.defaults and i >= given and n not in names] + [n for n in sig.kw_required if n not in names]
        if missing:
            return f"does not pass the required argument {', '.join(repr(n) for n in missing)}"
    return None


def _shallow(statements):
    """Statements of a module level, including those inside if, try, with, and loops, but not inside functions or classes."""
    for node in statements:
        yield node
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.AsyncWith, ast.AsyncFor)):
            yield from _shallow(node.body)
            yield from _shallow(getattr(node, "orelse", []))
        elif isinstance(node, ast.Try):
            for block in (node.body, node.orelse, node.finalbody, *(h.body for h in node.handlers)):
                yield from _shallow(block)
