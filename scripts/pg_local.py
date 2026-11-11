"""`python scripts/dev.py db`: local PostgreSQL in data/postgres for development; its URL goes into .env once, never on
screen. `--import-sqlite [path]` then copies an old SQLite store into it (scripts/sqlite_to_postgres.py).
The cluster code lives in `backend/local_postgres.py`, shared with the desktop app and the tests."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from backend.local_postgres import binary, free_port, start, stop  # noqa: E402,F401 - tests and azure_local use these


def main() -> int:
    """`python scripts/dev.py db`: local PostgreSQL in data/postgres; its URL goes into .env once, never on screen.
    `--import-sqlite [path]` then copies an old SQLite store into it (scripts/sqlite_to_postgres.py)."""
    root = Path(__file__).resolve().parents[1]
    url = start(root / "data" / "postgres")
    env_file = root / ".env"
    text = env_file.read_text(encoding="utf-8") if env_file.is_file() else ""
    if "ATLAS_DATABASE_URL=" not in text:
        env_file.write_text(text + ("" if text.endswith("\n") or not text else "\n") + f"ATLAS_DATABASE_URL={url}\n", encoding="utf-8")
    print("PostgreSQL is running on 127.0.0.1; ATLAS_DATABASE_URL is in .env.")
    if "--import-sqlite" in sys.argv:
        rest = sys.argv[sys.argv.index("--import-sqlite") + 1:]
        os.environ["ATLAS_DATABASE_URL"] = url
        return subprocess.run([sys.executable, str(root / "scripts" / "sqlite_to_postgres.py"), *rest[:1]], check=False).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
