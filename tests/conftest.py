"""Every test run uses a throwaway data directory and a throwaway PostgreSQL cluster. The app's real data is never touched.
Set ATLAS_TEST_DATABASE_URL to use an existing empty database instead (for example a CI service container)."""
import atexit
import os
import secrets
import shutil
import tempfile

_store = tempfile.mkdtemp(prefix="atlas-test-")
os.environ["ATLAS_DATA_DIR"] = _store
if os.environ.get("ATLAS_TEST_DATABASE_URL"):
    os.environ["ATLAS_DATABASE_URL"] = os.environ["ATLAS_TEST_DATABASE_URL"]
else:
    from scripts import pg_local

    _cluster = tempfile.mkdtemp(prefix="atlas-pg-")
    os.environ["ATLAS_DATABASE_URL"] = pg_local.start(_cluster)

    def _drop_cluster():
        from backend import db as _db
        _db.close()
        pg_local.stop(_cluster)
        shutil.rmtree(_cluster, ignore_errors=True)

    atexit.register(_drop_cluster)
os.environ["ATLAS_WORKSPACES"] = os.path.join(_store, "projects")
os.environ.setdefault("ATLAS_SECRET_KEY", "test-only-key")
os.environ["ATLAS_ADMIN_USERNAME"] = "qa-admin"
os.environ["ATLAS_ADMIN_PASSWORD"] = secrets.token_urlsafe(18)  # made fresh for each test session

from backend import db as database  # noqa: E402
from backend.core import files, prompts  # noqa: E402

database.migrate()
prompts.seed()
files.seed_templates()


def connect_test_repo(project_id: str):
    """A real git repository with one real file for tests that need a connected repository (the sandbox refuses without one)."""
    from backend.config import repo_dir
    from backend.repos import git

    repo = repo_dir(project_id)
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        git.init_snapshot(repo, "test repository")
    return repo
