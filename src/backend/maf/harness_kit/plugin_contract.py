"""Plugin contracts and gate checks as typed tools (docs/PHASE2_PLAN.md section 8, R5).

`describe_contract(path)` says which fields a plugin-owned file must have, read from the enabled plugins themselves: the
field names each `normalizeX(param)` function reads (hooks/src/*.ts), and the passages of the plugin's skills and
references that name the file. `check_gate(gate, app)` runs a plugin's own `check-gate` script on the workspace and
returns its report. Found on the agentic-qe live run (2026-11-12): requirements written with a field the plugin does not
read (`source_evidence`) failed Gate 1 three times; the contract was in the plugin all along.
ponytail: TypeScript is read with patterns, not parsed; a normalizer written another way shows no fields, only the passages.
"""
from __future__ import annotations

import re
from pathlib import Path

from agent_framework import ContextProvider, tool

from backend.core import plugins, script_runtime

NORMALIZER = re.compile(r"export function normalize(\w+)\((\w+)[^)]*\)[^{]*\{(.*?)\n\}", re.S)
MAX_PASSAGES = 6


def _plugin_roots() -> list[Path]:
    return [p.root for p in plugins.discover() if p.enabled]


def _fields(stem: str) -> list[tuple[str, list[str]]]:
    key = re.sub(r"[^a-z]", "", stem.lower())
    found = []
    for root in _plugin_roots():
        for source in (root / "hooks" / "src").glob("*.ts"):
            for name, param, body in NORMALIZER.findall(source.read_text(encoding="utf-8", errors="replace")):
                if name.lower() in key:
                    names = list(dict.fromkeys(re.findall(rf"\b{param}\??\.(\w+)", body)))
                    found.append((f"normalize{name} in {source.relative_to(root).as_posix()}", names))
    return found


def _passages(name: str) -> list[str]:
    out = []
    for root in _plugin_roots():
        for doc in sorted((root / "skills").glob("*/**/*.md")):
            lines = doc.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                if name in line and len(out) < MAX_PASSAGES:
                    out.append(f"{doc.relative_to(root).as_posix()}:{i + 1}\n" + "\n".join(lines[max(0, i - 2):i + 6]))
    return out


def describe(path: str) -> str:
    name = Path(path).name
    fields, passages = _fields(Path(path).stem), _passages(name)
    if not fields and not passages:
        return f"No enabled plugin describes {name}. Write it as the command's own instructions say."
    parts = [f"Contract for {name}, read from the enabled plugins:"]
    for where, names in fields:
        parts.append(f"Fields each item may have ({where}; one of each alias pair is enough): {', '.join(names)}")
    parts += [f"--- {p}" for p in passages]
    return "\n".join(parts)


def _gate_script() -> Path | None:
    # only a plugin that ships the hooks its script imports (a copied skill folder alone cannot run it)
    return next((s for root in _plugin_roots() if (root / "hooks" / "src").is_dir() for s in sorted((root / "skills").glob("*/scripts/check-gate.ts"))), None)


def check(ws, gate: int, app: str) -> str:
    script = _gate_script()
    if not script:
        return "No enabled plugin has a check-gate script."
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", app) or not 0 <= gate <= 5:
        return "Refused: app is a folder name under docs/qe and gate is 0 to 5."
    planned = script_runtime.plan(script, script.parent.parent)
    if planned.argv is None:
        return f"The check cannot run here: {planned.reason}"
    done = script_runtime.run([*planned.argv, "--gate", str(gate), "--app", app], cwd=ws.root, env=ws.env(), timeout=120)
    return f"exit {done['exit_code']}\n{(done['stdout'] + done['stderr']).strip()[-6000:]}"


class PluginContractProvider(ContextProvider):
    """Adds the two tools only when an enabled plugin brings what they read."""

    def __init__(self, ws):
        super().__init__("plugin_contracts")
        self.tools = []
        if not _plugin_roots():
            return

        @tool(name="describe_contract", description="Before writing a plugin-owned file (for example docs/qe/<app>/02-requirements/requirements.json), "
              "read which fields the plugin reads in it and its rules. Use the field names exactly.")
        def describe_contract(path: str) -> str:
            return describe(path)

        @tool(name="check_gate", description="Run the plugin's own gate check for gate 0-5 on docs/qe/<app> and return its report (PASS or the gaps).")
        def check_gate(gate: int, app: str) -> str:
            return check(ws, gate, app)

        self.tools = [describe_contract, check_gate]

    async def before_run(self, *, agent, session, context, state) -> None:
        if self.tools:
            context.extend_tools(self.source_id, self.tools)
