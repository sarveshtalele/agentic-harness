"""Paths and environment. ATLAS_DATA_DIR lets tests run against a throwaway store."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_HERE = Path(__file__).resolve()
# The folder that holds prompts/, skills/ and templates/: two levels up in the repo (src/backend/config.py), one level
# up in the Azure package's top-level backend/ copy, which `python -m uvicorn` imports first from wwwroot.
ROOT = next((p for p in _HERE.parents if (p / "prompts").is_dir()), _HERE.parents[2])
load_dotenv(ROOT / ".env")
from backend import keyvault  # noqa: E402

KEY_VAULT_LOADED = keyvault.load()  # Azure: secrets from Key Vault before any setting below is read (names only, never values)

_DATA = Path(os.environ.get("ATLAS_DATA_DIR", ROOT / "data"))
DATA_DIR = (_DATA if _DATA.is_absolute() else ROOT / _DATA).resolve()  # a relative path means relative to the repository, not the cwd
WORKSPACES = Path(os.environ.get("ATLAS_WORKSPACES", DATA_DIR / "projects")).resolve()
# PostgreSQL only (MASTER_PLAN Part 3, G5). Locally `python scripts/dev.py db` prints this URL; on Azure it comes from Key Vault.
DATABASE_URL = os.environ.get("ATLAS_DATABASE_URL", "")
DB_POOL_SIZE = int(os.environ.get("ATLAS_DB_POOL_SIZE", "10"))
CHECKPOINTS = DATA_DIR / "checkpoints"
RUNS = DATA_DIR / "runs"  # per run: rejected model replies under failures/, finished batches under parts/
LOGS = DATA_DIR / "logs"  # app-YYYY-MM-DD.jsonl, one file per day
LOG_RETENTION_DAYS = int(os.environ.get("ATLAS_LOG_RETENTION_DAYS", "30"))
TRACE_RETENTION_DAYS = int(os.environ.get("ATLAS_TRACE_RETENTION_DAYS", "30"))  # spans table, pruned at startup
PROMPTS_DIR = ROOT / "prompts"
SKILLS_DIR = Path(os.environ.get("ATLAS_SKILLS_DIR", ROOT / "skills")).resolve()  # the Azure package keeps skills/ beside prompts/
TEMPLATES_DIR = ROOT / "templates"
MAX_UPLOAD_BYTES = int(os.environ.get("ATLAS_MAX_UPLOAD_MB", "200")) * 1024 * 1024
RUN_TOKEN_LIMIT = int(os.environ.get("ATLAS_RUN_TOKEN_LIMIT", "50000000"))
# The most test cases a QE run keeps after design. P0 cases are never cut. What is left out is reported at the gate.
MAX_CASES = int(os.environ.get("ATLAS_MAX_CASES", "40"))
MODEL_TIMEOUT = int(os.environ.get("ATLAS_MODEL_TIMEOUT", "180"))
MODEL_RETRIES = int(os.environ.get("ATLAS_MODEL_RETRIES", "3"))
# LiteLLM answers an identical prompt from its cache, so a retry would get the same bad reply. Set 0 for endpoints that reject the field.
MODEL_NO_CACHE = os.environ.get("ATLAS_MODEL_NO_CACHE", "1") != "0"
MODEL_CONCURRENCY = int(os.environ.get("ATLAS_MODEL_CONCURRENCY", "4"))
# web (Azure: the shared server) or local (development and tests).
PROFILE = os.environ.get("ATLAS_PROFILE", "local")
MAX_SANDBOXES = int(os.environ.get("ATLAS_MAX_SANDBOXES", "5"))
# WAL needs shared memory, which network storage such as Azure App Service /home lacks. Use DELETE there.
ALLOWED_ORIGINS = {
    o.strip()
    for o in os.environ.get("ATLAS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
}

for path in (DATA_DIR, WORKSPACES, CHECKPOINTS, RUNS, LOGS):
    path.mkdir(parents=True, exist_ok=True)


def project_dir(project_id: str) -> Path:
    return WORKSPACES / project_id


def repo_dir(project_id: str) -> Path:
    return project_dir(project_id) / "repo"


def sandbox_dir(project_id: str) -> Path:
    return project_dir(project_id) / "sandbox"
