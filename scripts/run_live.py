"""Run live tests with the model configured in your local store (Settings page), without printing or exporting the key.

    python scripts/dev.py live tests/test_harness_discovery_eval.py [more pytest args]

The model's base URL, name and key are read from the local store and handed to one pytest child through its environment
only. The child gets a throwaway store, database and skills folder (tests/conftest.py), so a live run never touches your data.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.chdir(ROOT)

from backend.maf import llm  # noqa: E402  reads ATLAS_DATABASE_URL from .env like the app does

cfg = llm.current()
if not (cfg.get("api_key") and cfg.get("model")):
    sys.exit("No model is configured in your local store. Set it on the Settings page (or OPENAI_* in .env) first.")
env = {**os.environ, "OPENAI_BASE_URL": cfg["base_url"], "OPENAI_API_KEY": cfg["api_key"], "DEFAULT_MODEL": cfg["model"],
       "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)])}
for key in ("ATLAS_DATABASE_URL", "ATLAS_DATA_DIR", "ATLAS_SKILLS_DIR", "ATLAS_ADMIN_USERNAME", "ATLAS_ADMIN_PASSWORD", "ATLAS_SECRET_KEY",
            "ATLAS_BACKEND_URL", "ATLAS_WORKSPACES", "ATLAS_KEY_VAULT_URL"):
    env.pop(key, None)  # the child builds its own throwaway store
print(f"live run with model {cfg['model']}", flush=True)
args = sys.argv[1:] or ["tests"]
sys.exit(subprocess.run([sys.executable, "-m", "pytest", *args, "-m", "live", "-s", "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env).returncode)
