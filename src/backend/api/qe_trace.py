"""The QE cycle's traceability view (docs/PHASE2_PLAN.md R5, 12.5): requirement -> plan scenario -> designed case ->
generated test -> result, gaps first, with each gate's check and the run's evidence files.

Read from what the agentic-qe plugin writes in the project's workspace: `docs/qe/<app>/coverage-map.json`, built by the
plugin's own code from the documents on disk (never by a model), and `02-requirements/requirements.json` for each
requirement's quoted source line. Nothing is computed here that the plugin did not record; a missing file is an empty
view that says so. Files open read-only from inside the workspace.
"""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.api.common import _project
from backend.config import sandbox_dir
from backend.core import cli_workspaces
from backend.core.security import PathEscape, redact, safe_path

router = APIRouter()
EVIDENCE_DIR = "06-execution"
MAX_FILE = 5 * 1024 * 1024


def _root(project_id: str) -> Path:
    return (cli_workspaces.path_of(project_id) or sandbox_dir(project_id)).resolve()


def _quotes(app_dir: Path) -> dict[str, dict]:
    """Each requirement's source file, line and quote, under the field names the plugin's normalizer accepts."""
    # ponytail: the aliases of the plugin's normalizeRequirement (hooks/src/layout.ts); a renamed field there shows as no quote here
    path = app_dir / "02-requirements" / "requirements.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    items = data if isinstance(data, list) else data.get("requirements", []) if isinstance(data, dict) else []
    out = {}
    for r in items:
        if isinstance(r, dict) and r.get("id"):
            out[str(r["id"])] = {"file": str(r.get("sourceFile") or r.get("source_file") or ""), "line": r.get("lineNumber") or r.get("line_number"),
                                 "quote": redact(str(r.get("evidenceQuote") or r.get("quote") or ""))[:400]}
    return out


def _app(app_dir: Path) -> dict:
    data = json.loads((app_dir / "coverage-map.json").read_text(encoding="utf-8"))
    cov, quotes = data.get("coverage", {}), _quotes(app_dir)
    scenarios, cases, tests, results = cov.get("scenarios", []), cov.get("cases", []), cov.get("tests", []), cov.get("results", {})
    rows = []
    for r in cov.get("requirements", []):
        mine = [s for s in scenarios if r["id"] in s.get("requirementIds", [])]
        linked = [c for c in cases if set(c.get("scenarioIds", [])) & {s["id"] for s in mine}]
        cells = [{"case_id": c["id"], "level": c.get("level"), "tests": [t["path"] for t in tests if c["id"] in t.get("markers", [])],
                  "result": results.get(c["id"], "not run")} for c in linked]
        gap = "no scenario" if not mine else "no case" if not cells else "no test" if not any(c["tests"] for c in cells) else \
            "not run" if all(c["result"] == "not run" for c in cells) else "failed" if any(c["result"] == "failed" for c in cells) else ""
        rows.append({"id": r["id"], "priority": r.get("priority"), "text": redact(r.get("text", ""))[:300], "evidence": r.get("evidence", False),
                     "quote_found": r.get("quoteFound"), "source": quotes.get(r["id"], {}), "scenarios": [s["id"] for s in mine], "cases": cells, "gap": gap})
    rows.sort(key=lambda row: (row["gap"] == "", row["priority"] or "P9", row["id"]))
    evidence = app_dir / EVIDENCE_DIR
    files = sorted(str(p.relative_to(app_dir.parents[2]).as_posix()) for p in evidence.rglob("*") if p.is_file())[:200] if evidence.is_dir() else []
    return {"app": data.get("app") or app_dir.name, "approved_up_to": data.get("approvedUpTo", 0), "checks": data.get("checks", []),
            "counts": {k: len(cov.get(k, [])) for k in ("requirements", "scenarios", "cases", "tests")} | {"results": len(results)},
            "rows": rows, "orphan_tests": [t["path"] for t in tests if not t.get("markers")], "evidence": files, "problems": cov.get("problems", [])}


@router.get("/api/projects/{project_id}/qe/trace")
def trace(project_id: str):
    _project(project_id)
    base = _root(project_id) / "docs" / "qe"
    found = sorted(base.glob("*/coverage-map.json")) if base.is_dir() else []
    apps = []
    for path in found:
        try:
            apps.append(_app(path.parent))
        except (OSError, ValueError, KeyError) as exc:
            apps.append({"app": path.parent.name, "error": f"coverage-map.json could not be read: {type(exc).__name__}"})
    return {"apps": apps, "note": "" if apps else "No QE cycle has written a coverage map in this project's workspace yet."}


@router.get("/api/projects/{project_id}/qe/file")
def workspace_file(project_id: str, path: str):
    """A source, test or evidence file from the workspace, read-only."""
    _project(project_id)
    try:
        target = safe_path(_root(project_id), path)
    except PathEscape as exc:
        raise HTTPException(400, str(exc)) from exc
    if not target.is_file() or target.stat().st_size > MAX_FILE:
        raise HTTPException(404, "No such file in the workspace (or it is over 5 MB)")
    kind = mimetypes.guess_type(target.name)[0] or "text/plain"
    if not kind.startswith("image/"):
        kind = "text/plain; charset=utf-8"  # never served as HTML or script: repository content is untrusted
    return FileResponse(target, media_type=kind, headers={"Content-Disposition": f'inline; filename="{target.name}"', "X-Content-Type-Options": "nosniff"})
