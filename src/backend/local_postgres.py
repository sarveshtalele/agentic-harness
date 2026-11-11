"""A local PostgreSQL cluster in a folder (MASTER_PLAN Part 3, G5): the desktop app's database, the developer's
(`python scripts/dev.py db`), and the tests' throwaway one. It uses the PostgreSQL installed on the machine (Homebrew,
the official installer, apt, or the one GitHub's runners ship) and never touches a system service. It imports nothing
from the backend, so it can run before the settings are read.

The cluster listens on 127.0.0.1 only, with password (SCRAM) authentication. The password is random, kept in
`<folder>/.atlas-password` (owner-only), and returned only inside the connection URL.
"""
from __future__ import annotations

import glob
import os
import secrets
import shutil
import socket
import subprocess
import sys
from pathlib import Path

USER = "atlas"
CANDIDATES = ["/opt/homebrew/opt/postgresql@*/bin", "/usr/local/opt/postgresql@*/bin", "/opt/homebrew/bin", "/usr/lib/postgresql/*/bin",
              "/usr/pgsql-*/bin", r"C:\Program Files\PostgreSQL\*\bin"]


def binary(name: str) -> str:
    """Path of a PostgreSQL program (initdb, pg_ctl), or a clear error saying how to install PostgreSQL."""
    exe = name + (".exe" if os.name == "nt" else "")
    if found := shutil.which(name):
        return found
    for folder in [os.environ.get("PGBIN", "")] + sorted((d for c in CANDIDATES for d in glob.glob(c)), reverse=True):
        if folder and (Path(folder) / exe).is_file():
            return str(Path(folder) / exe)
    sys.exit(f"PostgreSQL's {name} was not found. Install PostgreSQL 16 or newer (macOS: brew install postgresql@17; Windows: the "
             "installer from postgresql.org; Linux: apt install postgresql), or set PGBIN to its bin folder.")


def _env() -> dict[str, str]:
    return {**os.environ, "LC_ALL": "C"}  # macOS: without a set locale the server stops with "postmaster became multithreaded"


def _run(argv: list[str], timeout: int = 120) -> None:
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False, env=_env())
    if done.returncode:
        sys.exit(f"{Path(argv[0]).name} failed: {(done.stderr or done.stdout).strip()[-600:]}")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(folder: Path, port: int | None = None, database: str = "agentic_qe") -> str:
    """Create the cluster if needed, start it, make the database; returns the connection URL."""
    folder = Path(folder).resolve()
    secret = folder / ".atlas-password"
    data = folder / "data"
    if not (data / "PG_VERSION").is_file():
        folder.mkdir(parents=True, exist_ok=True)
        secret.write_text(secrets.token_urlsafe(24), encoding="utf-8")
        os.chmod(secret, 0o600)
        _run([binary("initdb"), "-D", str(data), "-U", USER, "--auth=scram-sha-256", f"--pwfile={secret}", "-E", "UTF8", "--locale=C"])
    saved = folder / ".atlas-port"  # a developer cluster keeps its port, so the URL in .env stays right
    if not port:
        port = int(saved.read_text(encoding="utf-8")) if saved.is_file() else free_port()
    saved.write_text(str(port), encoding="utf-8")
    options = f"-p {port} -c listen_addresses=127.0.0.1" + ("" if os.name == "nt" else f" -k {folder}")
    if subprocess.run([binary("pg_ctl"), "-D", str(data), "status"], capture_output=True, timeout=30, check=False, env=_env()).returncode != 0:
        _run([binary("pg_ctl"), "-D", str(data), "-o", options, "-l", str(folder / "server.log"), "-w", "-t", "60", "start"])
    password = secret.read_text(encoding="utf-8").strip()
    import psycopg  # the backend's own driver

    admin = f"postgresql://{USER}:{password}@127.0.0.1:{port}/postgres"
    with psycopg.connect(admin, autocommit=True) as con:
        if not con.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            con.execute(f'CREATE DATABASE "{database}"')
    return f"postgresql://{USER}:{password}@127.0.0.1:{port}/{database}"


def stop(folder: Path) -> None:
    data = Path(folder) / "data"
    if (data / "PG_VERSION").is_file():
        subprocess.run([binary("pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"], capture_output=True, timeout=60, check=False, env=_env())
