"""PyInstaller entry point: runs the FastAPI app on loopback. The port comes from the Electron shell.

The database is PostgreSQL (MASTER_PLAN Part 3, G5). Unless ATLAS_DATABASE_URL is given, the app runs its own cluster in
the user's data folder with the PostgreSQL installed on this computer (backend/local_postgres.py), started before the
settings are read. Without an installed PostgreSQL it stops with a message that says how to install one.
"""
import multiprocessing
import os
from pathlib import Path

import uvicorn

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if not os.environ.get("ATLAS_DATABASE_URL"):
        from backend import local_postgres

        os.environ["ATLAS_DATABASE_URL"] = local_postgres.start(Path(os.environ.get("ATLAS_DATA_DIR", "data")) / "postgres")
    from backend.app import app

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ATLAS_BACKEND_PORT", "18765")), log_level="info")
