"""Registry sources in the workflow engine: each workflow in `engine.REGISTRY`, its stages, who performs them, and gates.

The definition function only builds dataclasses, so it is called to list the stages; no stage runs. Who performs a stage
is read with `ast`: every `AgentCall(run_id, project_id, "<agent>")` string literal in the stage's own module (the whole
package for a package such as `qe/generate`), or in the stage function alone when one module holds several stages
(`ba.py`, `bug_scan.py`). A gate is linked only where the code states its number: an int passed as a `gate` parameter,
or a `"gate": <int>` in the approval function's reply. Gate names come from `core/gates.GATES`.
"""
from __future__ import annotations

import ast
import inspect
import sys
import textwrap
from collections import Counter
from pathlib import Path

from backend.core.registry.model import Cap, Graph, digest, one_line, rel


def _agent_literals(text: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "AgentCall" and len(node.args) > 2:
            arg = node.args[2]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value not in found:
                found.append(arg.value)
    return found


def _scope(fn, shared: bool) -> tuple[str, str]:
    """The source a stage's agents are read from, and its path."""
    path = Path(inspect.getsourcefile(fn))
    if shared:
        return textwrap.dedent(inspect.getsource(fn)), rel(path)
    if path.name == "__init__.py":
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(path.parent.rglob("*.py"))), rel(path.parent)
    return path.read_text(encoding="utf-8"), rel(path)


def _approvals(factory) -> dict[str, ast.expr]:
    """Stage id -> the `approval=` expression of its StageSpec in the definition function."""
    found = {}
    for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(factory)))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "StageSpec" and node.args and isinstance(node.args[0], ast.Constant):
            for keyword in node.keywords:
                if keyword.arg == "approval":
                    found[node.args[0].value] = keyword.value
    return found


def _gate_numbers(expr: ast.expr | None, names: dict) -> list[int]:
    if expr is None:
        return []
    found = []
    for node in ast.walk(expr):
        callee = names.get(getattr(node.func, "id", "")) if isinstance(node, ast.Call) else None
        if callee and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, int):
            params = list(inspect.signature(callee).parameters)
            if params and params[0] == "gate":
                found.append(node.args[0].value)
        if isinstance(node, ast.Name) and inspect.isfunction(target := names.get(node.id)):
            for inner in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(target)))):
                if isinstance(inner, ast.Dict):
                    for key, value in zip(inner.keys, inner.values):
                        if isinstance(key, ast.Constant) and key.value == "gate" and isinstance(value, ast.Constant) and isinstance(value.value, int):
                            found.append(value.value)
    return sorted(set(found))


def gate_sources(g: Graph) -> None:
    from backend.core import gates

    for number, (name, description) in sorted(gates.GATES.items()):
        g.add(Cap("gate", f"G{number}", f"G{number}", f"{name}: {description}. A named human approves it.", rel(gates.__file__), digest(f"{number}|{name}|{description}")))


def workflow_sources(g: Graph) -> None:
    from backend.maf.engine.registry import REGISTRY, _ensure_workflows

    _ensure_workflows()
    for name in sorted(REGISTRY):
        factory = REGISTRY[name]
        definition = factory()
        stages = [(s.id, s.fn, s.label) for s in definition.stages]
        if definition.fan_out:
            stages.append((definition.fan_out.merge_id, definition.fan_out.merge_fn, definition.fan_out.merge_id))
        wid = g.add(Cap("workflow", name, name, one_line(inspect.getdoc(factory)), rel(inspect.getsourcefile(factory)), digest(inspect.getsource(factory)),
                        meta={"stages": [s[0] for s in stages]}))
        approvals, names = _approvals(factory), vars(sys.modules[factory.__module__])
        per_module = Counter(fn.__module__ for _, fn, _ in stages)
        for index, (stage, fn, label) in enumerate(stages):
            text, source = _scope(fn, per_module[fn.__module__] > 1)
            sid = g.add(Cap("stage", stage, f"{name}.{stage}", label or stage, source, digest(text), meta={"workflow": name, "order": index, "function": fn.__name__}))
            g.link(wid, sid, "contains", index)
            for agent in _agent_literals(text):
                g.link_to(sid, "agent", agent, "performed_by")
            for number in _gate_numbers(approvals.get(stage), names):
                g.link_to(sid, "gate", f"G{number}", "gates")
