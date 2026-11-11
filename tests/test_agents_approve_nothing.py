"""CI gate 4 (plan Section 3.2): agents approve nothing.

Static: outside the human-facing routes and the engine, no module may call a gate or approval decision, approve a
document, resolve an in-memory approval, or write the gates/approvals tables, however the function was imported.
Behavioural: every registered harness tool is run against a real project and must leave gates, approvals and
document status unchanged.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

DECIDE_ALLOWED = {
    "backend/core/gates.py": "defines decide",
    "backend/maf/engine/__init__.py": "applies a decision a signed-in human sent through the API",
    "backend/api/governance/decisions.py": "human route, signer from auth.signer()",
    "backend/api/runs.py": "human route, signer from auth.signer()",
    "backend/core/documents.py": "set_status cascades a human document approval",
}
APPROVE_DOC_ALLOWED = {"backend/api/documents/versions.py", "backend/maf/workflows/ba.py", "backend/core/documents.py"}
SQL_WRITE = re.compile(r"""(?i)\b(?:(?:INSERT(?:\s+OR\s+\w+)?|REPLACE)\s+INTO|UPDATE)\s+["`]?(?:gates|approvals)\b""")
SQL_ALLOWED = {"backend/core/gates.py", "backend/maf/engine/__init__.py", "backend/maf/engine/execution.py"}
SQL_KNOWN_LEGACY: set[str] = set()  # the seed writer was retired 2026-11-10 (owner yes)
DECISION_MODULES = {"gates", "engine", "approval_manager", "global_approval_manager"}
DECISION_FUNCS = {"decide", "resolve_approval"}


def _aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Names bound to decision modules, and names bound directly to decision functions."""
    modules, funcs = set(DECISION_MODULES), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name in DECISION_MODULES:
                    modules.add(a.asname or a.name)
                if a.name in DECISION_FUNCS and (node.module or "").split(".")[-1] in DECISION_MODULES:
                    funcs.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[-1] in DECISION_MODULES:
                    modules.add(a.asname or a.name.split(".")[-1])
    return modules, funcs


def _owner(expr: ast.AST) -> str:
    """Last name of a dotted owner: `self.engine` and `backend.core.gates` give 'engine' and 'gates'."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return ""


def _approves_document(call: ast.Call) -> bool:
    values = call.args[1:2] + [k.value for k in call.keywords if k.arg == "status"]
    return any(isinstance(v, ast.Constant) and v.value == "approved" for v in values)


def static_offenders() -> list[str]:
    found = []
    for path in sorted((SRC / "backend").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel, text = path.relative_to(SRC).as_posix(), path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
        modules, funcs = _aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            decides = (isinstance(fn, ast.Name) and fn.id in funcs) or \
                      (isinstance(fn, ast.Attribute) and fn.attr in DECISION_FUNCS and _owner(fn.value) in modules)
            if decides and rel not in DECIDE_ALLOWED:
                found.append(f"{rel}:{node.lineno} decision call")
            if isinstance(fn, ast.Attribute) and fn.attr == "set_status" and _approves_document(node) and rel not in APPROVE_DOC_ALLOWED:
                found.append(f"{rel}:{node.lineno} document approval")
        if SQL_WRITE.search(text) and rel not in SQL_ALLOWED | SQL_KNOWN_LEGACY:
            found.append(f"{rel}: writes gates/approvals with SQL")
    return found


def test_no_module_outside_the_human_routes_decides():
    offenders = static_offenders()
    assert not offenders, "Only a signed-in human may decide gates or approvals:\n" + "\n".join(offenders)


def test_static_check_sees_aliased_and_keyword_forms():
    """The check must catch the bypasses a plain name match misses."""
    planted = ("from backend.core.gates import decide as d\nimport backend.maf.engine as eng\n"
               "d(1)\neng.decide(2)\nself.engine.decide(3)\ndocuments.set_status(x, status='approved')\n")
    tree = ast.parse(planted)
    modules, funcs = _aliases(tree)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    hits = sum(1 for c in calls if (isinstance(c.func, ast.Name) and c.func.id in funcs)
               or (isinstance(c.func, ast.Attribute) and c.func.attr in DECISION_FUNCS and _owner(c.func.value) in modules))
    assert hits == 3 and any(_approves_document(c) for c in calls)
    assert SQL_WRITE.search('REPLACE INTO "gates" VALUES (1)') and SQL_WRITE.search("insert or ignore into approvals")


def _snapshot(project_id: str) -> tuple:
    from backend.db import db
    with db() as con:
        gates = con.execute("SELECT * FROM gates WHERE project_id=? ORDER BY 1", (project_id,)).fetchall()
        approvals = con.execute("SELECT id, status FROM approvals WHERE project_id=? ORDER BY 1", (project_id,)).fetchall()
        docs = con.execute("SELECT id, status FROM documents WHERE project_id=? AND status='approved' ORDER BY 1", (project_id,)).fetchall()
    return [tuple(r) for r in gates], [tuple(r) for r in approvals], [tuple(r) for r in docs]


@pytest.mark.asyncio
async def test_every_harness_tool_leaves_gates_and_approvals_unchanged():
    """Every tool the MAF harness can call, invoked with approval-shaped arguments, changes no gate, approval or document status."""
    from backend.db import db, now
    from backend.maf import tools
    from tests.conftest import connect_test_repo

    pid = "prj_gate4_behaviour"
    with db() as con:
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) "
                    "VALUES (?, 'Gate 4 behaviour', '', ?, ?, 0, 'admin')", (pid, now(), now()))
    connect_test_repo(pid)
    started = []

    def start_run(*args, **kwargs):  # a workflow start is recorded, not run: runs open gates for humans, never decide them
        started.append(args)
        raise RuntimeError("not started in this test")

    every = tools.repo_tools(pid) + tools.document_tools(pid) + tools.chat_tools(pid, "thr_gate4", start_run) + tools.harness_tools(pid, "thr_gate4", start_run)
    assert every, "no harness tools registered, so the check would prove nothing"
    before = _snapshot(pid)
    for tool in every:
        try:
            await tool.invoke(arguments={"approval_id": "appr_gate4", "approved": True, "gate": 4, "decision": "approve"})
        except Exception:  # a refusal or a missing argument is fine; only state changes matter here
            pass
    assert _snapshot(pid) == before
