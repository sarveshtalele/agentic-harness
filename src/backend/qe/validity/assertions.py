"""V5: assertion integrity by AST. A test needs a real assertion, no tautology, no skip, and a check of its case's expected result."""
from __future__ import annotations

import ast
import re

from backend.qe import execution

SKIP = re.compile(r"\b(?:pytest\.(?:mark\.)?(?:skip|skipif|xfail|importorskip)|unittest\.skip\w*|skipTest)\b|@\s*Disabled")
TOKEN = re.compile(r"""(?<![\w.])-?\d+(?:\.\d+)?(?![\w])|"([^"\n]{1,60})"|'([^'\n]{1,60})'|\b\w*(?:Error|Exception|Warning)\b|\b(?:true|false|none|null)\b""", re.I)
IGNORED = {"error", "exception", "warning"}


def _tautology(test: ast.expr) -> bool:
    if isinstance(test, ast.Constant):
        return bool(test.value) or test.value is None  # assert True, assert 1, assert "x"
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], (ast.Eq, ast.Is, ast.GtE, ast.LtE)):
        return ast.dump(test.left) == ast.dump(test.comparators[0])  # assert x == x
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return isinstance(test.operand, ast.Constant) and not test.operand.value  # assert not False
    return False


def _tokens(expected: str) -> list[str]:
    found = [m.group(1) or m.group(2) or m.group(0) for m in TOKEN.finditer(expected or "")]
    return [t.lower().replace("null", "none") for t in found if t.lower() not in IGNORED]


def _assertion_text(func: ast.AST) -> tuple[list[str], int]:
    """The source text of each real assertion in a test, plus how many tautologies it has. One level of assignments is followed, so `want = 5; assert x == want` counts."""
    assigned = {t.id: ast.unparse(n.value) for n in ast.walk(func) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    texts, tautologies = [], 0
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            if _tautology(node.test):
                tautologies += 1
                continue
            text = ast.unparse(node.test)
            texts.append(text + " " + " ".join(assigned.get(n.id, "") for n in ast.walk(node.test) if isinstance(n, ast.Name)))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            texts += [ast.unparse(i.context_expr) for i in node.items if re.search(r"\b(?:raises|warns|assertRaises\w*)\b", ast.unparse(i.context_expr))]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
            texts.append(ast.unparse(node))  # unittest style, and assertion helpers such as assert_called_with
    return texts, tautologies


def _python(path: str, code: str, expected: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # V3 reports the syntax error
    if skip := SKIP.search(ast.unparse(tree)):
        return f"{path}: uses a skip or xfail marker ({skip.group(0)}). Remove it and make the test run and assert"
    tests = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]
    if not tests:
        return f"{path}: has no test function. Add a function named test_<case id>_<what> that calls the code and asserts its result"
    seen: list[str] = []
    for func in tests:
        texts, tautologies = _assertion_text(func)
        if not texts:
            what = "only a tautology such as assert True or assert x == x" if tautologies else "no assertion"
            return f"{path}:{func.lineno}: {func.name} has {what}. Assert the value the case expects, for example assert result == <expected>"
        seen += texts
    return _expected_problem(path, seen, expected)


def _expected_problem(path: str, texts: list[str], expected: str) -> str | None:
    wanted = _tokens(expected)
    joined = " ".join(texts).lower()
    # ponytail: any one literal of the expected result (a number, quoted text, exception name, true/false/none) must appear in an assertion, or in a value assigned to a name it uses. A result described only in words cannot be checked. Upgrade: run the test against a seeded fault
    if wanted and not any(re.search(rf"(?<![\w.]){re.escape(t)}(?![\w])", joined) for t in wanted):
        return f"{path}: no assertion checks the case's expected result ({expected.strip()[:80]!r}). Assert one of: {', '.join(dict.fromkeys(wanted))[:80]}"
    return None


def integrity(path: str, code: str, expected: str) -> dict:
    if path.endswith(".py"):
        message = _python(path, code, expected)
    elif execution.WEAKENING.search(code):
        message = f"{path}: uses a skip, .only or tautological assertion. Remove it and assert the expected result"
    elif not execution.ASSERTION.search(code):
        message = f"{path}: has no assertion. Add expect(...) on the value the case expects"
    else:
        message = _expected_problem(path, [code], expected)
    return {"status": "FAIL", "message": message} if message else {"status": "PASS", "message": "real assertions, no skip"}
