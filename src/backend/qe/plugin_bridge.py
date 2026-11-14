"""The QE Cycle's link to the agentic-qe plugin: its skill text as a guide, its files, its gate check as a sensor.

A stage reads the plugin skill before the model acts (guide), writes the plugin's own files under
`<project>/docs/qe/<app>/`, and runs the plugin's `check-gate.ts` on them (computational sensor: quotes found on disk,
coverage rules, the pandas/numpy validator). Design: docs/STABLE_BUILD_PLAN.md Part B.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from backend.config import DATA_DIR, ROOT, project_dir
from backend.core import script_runtime
from backend.core.security import redact, safe_path
from backend.qe.execution.runners import clean_env

PLUGIN = ROOT / "plugins" / "agentic-qe"
CHECK_GATE = PLUGIN / "skills" / "tracing-coverage" / "scripts" / "check-gate.ts"
HOME = DATA_DIR / "qe-plugin-home"  # the plugin's ~/.agentic-qe (ledger anchors, validator venv) stays in the data folder
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def app_name(project_id: str) -> str:
    """The plugin's `<app>`: letters, digits, dot, dash, underscore; at most 64."""
    return (re.sub(r"[^A-Za-z0-9._-]+", "-", project_id).strip("-.") or "app")[:64]


def guide(*skills: str, limit: int = 12_000) -> str:
    """The named plugin skills' instructions and references, front matter removed, as one guide for the prompt."""
    parts = []
    for name in skills:
        folder = PLUGIN / "skills" / name
        files = [folder / "SKILL.md", *sorted((folder / "references").glob("*.md"))]
        for path in files:
            if path.is_file():
                parts.append(f"## {name}/{path.relative_to(folder).as_posix()}\n{FRONT_MATTER.sub('', path.read_text(encoding='utf-8')).strip()}")
    if not parts:
        raise FileNotFoundError(f"agentic-qe plugin skills not found: {', '.join(skills)} under {PLUGIN / 'skills'}")
    return "\n\n".join(parts)[:limit]  # ponytail: plain cut; the pilot's skills are about 6 KB


def write(project_id: str, app: str, relative: str, obj) -> Path:
    """Write one plugin file (JSON) under the project's docs/qe/<app>/, through the path guard."""
    path = safe_path(project_dir(project_id), f"docs/qe/{app}/{relative}", for_write=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def requirements_file(kept: list[dict]) -> dict:
    """The platform's verified requirements in the plugin's requirements.json shape (paths relative to the project)."""
    return {"requirements": [{
        "id": r["id"], "title": r.get("title", ""), "text": r.get("statement", ""), "priority": r.get("priority", ""),
        "source_file": f"repo/{r['file']}" if r.get("file") else "", "line_number": r.get("line") or 0, "quote": r.get("quote") or "",
    } for r in kept]}


def scenario_id(area_id: str, n: int = 1) -> str:
    """The plugin's plan scenario id for a platform plan area: SC-<AREA>-NNN."""
    key = "-".join(re.findall(r"[A-Z0-9]+", area_id.upper())) or "AREA"
    return f"SC-{key}-{n:03d}"


def plan_file(plan: dict) -> dict:
    """The platform's plan in the plugin's plan.json shape: one scenario per area, skipped levels with their reasons."""
    return {"strategy": plan.get("strategy", ""),
            "scenarios": [{"id": scenario_id(a["id"]), "area": a["name"], "title": a["name"], "level": a["level"],
                           "priority": a["risk"], "requirementIds": a["requirement_ids"]} for a in plan["areas"]],
            "skippedLevels": [{"level": k, "reason": v} for k, v in plan.get("skipped_levels", {}).items()]}


def check_gate(project_id: str, app: str, gate: int) -> dict:
    """Run the plugin's check-gate.ts. Returns {ok, gaps, missing, validator, error}; ok is False whenever it cannot run."""
    planned = script_runtime.plan(CHECK_GATE, CHECK_GATE.parent.parent)
    if not planned.argv:
        return {"ok": False, "gaps": [], "missing": [], "validator": None, "error": f"check-gate.ts cannot run: {planned.reason}"}
    HOME.mkdir(parents=True, exist_ok=True)
    root = project_dir(project_id)
    # the platform's own Python first on PATH: the plugin's validator looks for python3 with pandas and numpy
    env = clean_env({"HOME": str(HOME), "USERPROFILE": str(HOME), "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")})
    done = script_runtime.run([*planned.argv, "--gate", str(gate), "--app", app, "--root", str(root), "--json"], cwd=root, env=env)
    try:
        out = json.loads(done["stdout"])
    except (json.JSONDecodeError, TypeError):
        return {"ok": False, "gaps": [], "missing": [], "validator": None,
                "error": redact(f"check-gate.ts exit {done['exit_code']}: {(done['stderr'] or done['stdout'])[-800:]}")}
    return {"ok": bool(out.get("ok")), "gaps": out.get("gaps", []), "missing": out.get("missing", []),
            "validator": out.get("validator"), "error": None}
