"""V2b: no invented inputs or messages, and V4 async misuse. Static checks for what only execution would otherwise show.

Seen live (2026-11-14): tests called calculators named 'interest' and 'tvm' that the repository does not have, asserted
error texts the code never produces, used a sync httpx client on an async transport, and forgot `await`.
"""
from __future__ import annotations

import ast
import difflib
import re
from pathlib import Path

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]{1,40}$")
REQUEST = {"get", "post", "put", "patch", "delete", "request", "head", "options"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "agentic_qe"}
SOURCES = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".java", ".cs", ".go"}
QUOTED = re.compile(r"""(?:"([^"\\\n]{1,200})"|'([^'\\\n]{1,200})'|`([^`\\]{1,200})`)""")
_cache: dict[str, tuple[set[str], str]] = {}


def vocabulary(worktree: Path) -> tuple[set[str], str]:
    """Names and string literals in the repository's code (not comments or docstrings), and all its literals as one text.

    ponytail: cached per worktree for the life of the process; a run does not change the code under test.
    """
    key = str(worktree)
    if key in _cache:
        return _cache[key]
    names: set[str] = set()
    literals: list[str] = []
    for path in worktree.rglob("*"):
        if path.suffix not in SOURCES or not path.is_file() or SKIP_DIRS & set(path.relative_to(worktree).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            docs = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
            for n in ast.walk(tree):
                if isinstance(n, ast.Name):
                    names.add(n.id)
                elif isinstance(n, ast.Attribute):
                    names.add(n.attr)
                elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(n.name)
                elif isinstance(n, ast.arg):
                    names.add(n.arg)
                elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                    literals.append(n.value)
        else:
            literals += [a or b or c for a, b, c in QUOTED.findall(text)]
            names |= set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", re.sub(r"//.*|/\*.*?\*/", "", text, flags=re.S)))
    for lit in literals:
        names |= {lit} | set(re.findall(r"[A-Za-z_][A-Za-z0-9_\-]*", lit))
    _cache[key] = (names, "\n".join(literals))
    return _cache[key]


def _values(node: ast.AST) -> list[str]:
    """String constants used as inputs: call arguments, payload keys and values, URL path segments."""
    found = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value.strip()
            if v.startswith("/"):
                found += [s for s in v.split("?")[0].split("/") if s and IDENT.match(s) and not s.isdigit()]
            elif IDENT.match(v):
                found.append(v)
    return found


def _input_calls(tree: ast.AST, repo_names: set[str]) -> list[ast.Call]:
    imported = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and not n.module.startswith(("pytest", "httpx", "json", "pathlib", "unittest"))
                for a in n.names} & repo_names
    calls = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if (isinstance(f, ast.Attribute) and f.attr in REQUEST) or (isinstance(f, ast.Name) and f.id in imported):
                calls.append(n)
    return calls


def _asserted_texts(tree: ast.AST) -> list[str]:
    """Text constants an assertion compares against (equality, `in`, startswith): an expected message."""
    compared = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert):
            for c in ast.walk(n.test):
                if isinstance(c, ast.Compare):
                    compared += [c.left, *c.comparators]
                elif isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in ("startswith", "endswith"):
                    compared += c.args
    return [c.value.strip() for c in compared if isinstance(c, ast.Constant) and isinstance(c.value, str) and len(c.value.strip()) >= 6 and re.search(r"[A-Za-z]{3}", c.value)]


def invented(worktree: Path, path: str, code: str, case: dict, quote: str) -> dict:
    """V2b for a Python test. Negative and Exception cases may use invalid inputs on purpose, so only their messages are checked."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"status": "NOT CHECKED", "message": "the file does not parse (V3 reports it)"}
    names, corpus = vocabulary(worktree)
    given = " ".join(str(case.get(k, "")) for k in ("test_data", "steps", "expected_result", "precondition", "scenario")) + " " + quote
    known = names | set(re.findall(r"[A-Za-z_][A-Za-z0-9_\-]*", given))
    problems = []
    if not str(case.get("type", "")).startswith(("Negative", "Exception")):
        bad = sorted({v for call in _input_calls(tree, names) for v in _values(call) if v not in known})
        if bad:
            near = sorted({m for v in bad for m in difflib.get_close_matches(v, [n for n in names if IDENT.match(n)], n=3, cutoff=0.6)})
            problems.append(f"uses input value(s) {', '.join(map(repr, bad[:6]))} that appear nowhere in the repository's code or the requirement. "
                            f"Use values the code defines" + (f", for example {', '.join(map(repr, near[:6]))}" if near else ""))
    wrong = sorted({t for t in _asserted_texts(tree) if t not in corpus and t not in given and not any(t in lit for lit in corpus.splitlines())})
    if wrong:
        problems.append(f"asserts text the code never produces: {', '.join(map(repr, wrong[:4]))}. Assert the exact message the code returns (search the code for it), or the status code")
    return {"status": "FAIL", "message": f"{path}: " + "; ".join(problems)} if problems else {"status": "PASS", "message": "inputs and expected messages exist in the code or the requirement"}


def async_misuse(code: str) -> list[str]:
    """V4 additions: a sync httpx client on an async ASGI transport, and an async client's request that is not awaited."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    text = ast.unparse(tree)
    if "ASGITransport" in text and re.search(r"httpx\.Client\(|(?<!Async)\bClient\(transport", text):
        out.append("uses a sync httpx.Client with httpx.ASGITransport, which is async only. Use `async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:` in an async test and await each request")
    async_clients = {i.optional_vars.id for n in ast.walk(tree) if isinstance(n, (ast.AsyncWith, ast.With)) for i in n.items
                     if isinstance(i.optional_vars, ast.Name) and "AsyncClient" in ast.unparse(i.context_expr)}
    awaited = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Await)}
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in REQUEST and isinstance(n.func.value, ast.Name)
                and n.func.value.id in async_clients and id(n) not in awaited):
            out.append(f"line {n.lineno}: {ast.unparse(n.func)}(...) on an AsyncClient is not awaited, so it returns a coroutine. Write `await {ast.unparse(n.func)}(...)`")
    return out
