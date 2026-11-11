"""Session fixture and constants for the live target repository sandbox tests."""

from __future__ import annotations

import shutil

import pytest

from backend.config import ROOT, repo_dir, sandbox_dir
from backend.db import db, now
from backend.repos import sandbox, git, ingest


TARGET_PROJECT_ID = "prj_mcp_market"


TARGET_NAME = "MCP Server Market"


VALIDATION_BRANCH = "test/harness-qe-validation"


CACHED_REPO = ROOT / "data" / "projects" / TARGET_PROJECT_ID / "repo"


CACHED_SANDBOX = ROOT / "data" / "projects" / TARGET_PROJECT_ID / "sandbox"


@pytest.fixture(scope="session", autouse=True)
def setup_target_project_and_sandbox():
    """Ensure prj_mcp_market exists in the session DB and initialize its repo and sandbox."""
    # 1. Register project in database
    with db() as con:
        p = con.execute("SELECT id FROM projects WHERE id=?", (TARGET_PROJECT_ID,)).fetchone()
        if not p:
            con.execute(
                "INSERT INTO projects (id, name, description, owner_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (TARGET_PROJECT_ID, TARGET_NAME, "MCP Server Market with enterprise control room", "admin", now(), now()),
            )

    r_dir = repo_dir(TARGET_PROJECT_ID)
    s_dir = sandbox_dir(TARGET_PROJECT_ID)

    # 2. Ingest or clone repo
    if not r_dir.exists() or not (r_dir / ".git").exists():
        if CACHED_REPO.exists() and (CACHED_REPO / ".git").exists():
            r_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(CACHED_REPO, r_dir, symlinks=True)
        else:
            ingest.from_git(TARGET_PROJECT_ID, "https://github.com/sarveshtalele/mcp-server-market")

    # 3. Initialize sandbox
    if not s_dir.exists() or not (s_dir / ".git").exists():
        if CACHED_SANDBOX.exists() and (CACHED_SANDBOX / ".git").exists():
            s_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(CACHED_SANDBOX, s_dir, symlinks=True)
        else:
            sandbox.initialize_sandbox(TARGET_PROJECT_ID)

    # 4. Ensure validation branch exists and is checked out
    current_branch = git.run(["branch", "--show-current"], cwd=s_dir, check=False)
    if current_branch != VALIDATION_BRANCH:
        sandbox.create_branch(TARGET_PROJECT_ID, VALIDATION_BRANCH)

    # 5. Ensure feature endpoint and tests are present
    main_py = s_dir / "backend" / "app" / "main.py"
    if main_py.exists() and "/health/diagnostic" not in main_py.read_text(encoding="utf-8"):
        diag_endpoint = """

@app.get("/health/diagnostic", tags=["meta"])
def health_diagnostic() -> dict:
    \"\"\"Deep diagnostic readiness endpoint for QE pipelines and container orchestrators.\"\"\"
    from sqlalchemy import text
    from core.database import engine

    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ready" if db_ok else "degraded",
        "checks": {
            "database": "connected" if db_ok else "error",
            "mcp_protocol": PROTOCOL_VERSION,
            "agent_gateway": settings.mcp_gateway_url,
            "modules_loaded": len(_MODULES),
        },
        "schema_version": "1.0.0",
    }
"""
        with open(main_py, "a", encoding="utf-8") as f:
            f.write(diag_endpoint)

    conftest_py = s_dir / "backend" / "tests" / "conftest.py"
    if conftest_py.exists():
        ctext = conftest_py.read_text(encoding="utf-8")
        if "from mcp import Client, Implementation" in ctext and "except ImportError:" not in ctext:
            ctext = ctext.replace(
                "from mcp import Client, Implementation",
                "try:\n    from mcp import Client, Implementation\nexcept ImportError:\n    from mcp.client.session import ClientSession as Client\n    from mcp.types import Implementation"
            )
            conftest_py.write_text(ctext, encoding="utf-8")

    test_file = s_dir / "backend" / "tests" / "test_health_and_schema_validation.py"
    if not test_file.exists():
        if (CACHED_SANDBOX / "backend" / "tests" / "test_health_and_schema_validation.py").exists():
            shutil.copyfile(
                CACHED_SANDBOX / "backend" / "tests" / "test_health_and_schema_validation.py",
                test_file
            )

    # Commit any uncommitted changes
    sandbox.commit_changes(TARGET_PROJECT_ID, "feat(qe): add health diagnostics endpoint and schema validation suite")
