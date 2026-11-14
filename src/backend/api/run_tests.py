"""Download of a QE run's generated tests with their validity result."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.config import project_dir
from backend.maf import engine
from backend.qe import plugin_bridge
from backend.qe.validity import bundle

router = APIRouter()


@router.get("/api/runs/{run_id}/tests.zip")
def tests_zip(run_id: str):
    """tests/ (valid), needs-review/ (invalid), VALIDATION.md and the plugin's coverage-map.md. Ownership is the /api/runs/<id> rule in core/auth."""
    run = engine.get(run_id)
    state = run["state"]
    if not state.get("validation"):
        raise HTTPException(400, "This run has no validated tests yet. They are checked at the end of the Generate stage and saved when Gate 4 is approved")
    root = Path(state["worktree"])
    if not root.exists():
        raise HTTPException(410, "The worktree for this run no longer exists")
    coverage = project_dir(run["project_id"]) / "docs" / "qe" / plugin_bridge.app_name(run["project_id"]) / "coverage-map.md"
    body = bundle.build(root, state["validation"], state.get("framework", ""), root / "tests/agentic_qe/fixtures.json", coverage)
    return Response(body, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="tests-{run_id[-6:]}.zip"'})
