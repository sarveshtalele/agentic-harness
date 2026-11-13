"""`python scripts/dev.py db`: local PostgreSQL in data/postgres for development; its URL goes into .env once, never on
screen. `--import-sqlite [path]` then copies an old SQLite store into it (scripts/sqlite_to_postgres.py).
The cluster code lives in `backend/local_postgres.py`, shared with the tests."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from backend.local_postgres import binary, free_port, start, stop  # noqa: E402,F401 - tests and azure_local use these


LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def local_url(url: str) -> bool:
    """True for an empty URL or one on this computer: those `dev.py db` and `dev.py up` may replace."""
    return not url or urlsplit(url).hostname in LOOPBACK


def write_url(env_file: Path, url: str) -> str:
    """Put the cluster's URL in .env, replacing a stale local one; a remote database (Azure) is left alone."""
    text = env_file.read_text(encoding="utf-8") if env_file.is_file() else ""
    lines = text.splitlines()
    active = [line for line in lines if line.strip().startswith("ATLAS_DATABASE_URL=")]
    if any(not local_url(line.split("=", 1)[1].strip().strip('"\'')) for line in active):
        return "ATLAS_DATABASE_URL in .env points to another server, so it was left as is."
    kept = [line for line in lines if line not in active]
    env_file.write_text("\n".join(kept + [f"ATLAS_DATABASE_URL={url}"]) + "\n", encoding="utf-8")
    return "ATLAS_DATABASE_URL is in .env."


def main() -> int:
    """`python scripts/dev.py db`: local PostgreSQL in data/postgres; its URL goes into .env once, never on screen.
    `--import-sqlite [path]` then copies an old SQLite store into it (scripts/sqlite_to_postgres.py)."""
    root = Path(__file__).resolve().parents[1]
    url = start(root / "data" / "postgres")
    print(f"PostgreSQL is running on 127.0.0.1. {write_url(root / '.env', url)}")
    if os.environ.get("ATLAS_DATABASE_URL") and local_url(os.environ["ATLAS_DATABASE_URL"]):
        print("Note: ATLAS_DATABASE_URL is also set in your system environment, which wins over .env. `dev.py up` ignores a local one; "
              "remove it from the system environment if other tools use it.")
    if "--import-sqlite" in sys.argv:
        rest = sys.argv[sys.argv.index("--import-sqlite") + 1:]
        os.environ["ATLAS_DATABASE_URL"] = url
        return subprocess.run([sys.executable, str(root / "scripts" / "sqlite_to_postgres.py"), *rest[:1]], check=False).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
