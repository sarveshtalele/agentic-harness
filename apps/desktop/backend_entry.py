"""PyInstaller entry point: runs the FastAPI app on loopback. The port comes from the Electron shell."""
import multiprocessing
import os

import uvicorn

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from backend.app import app

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ATLAS_BACKEND_PORT", "18765")), log_level="info")
