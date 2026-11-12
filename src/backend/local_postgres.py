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


def _say(text: str) -> None:
    print(f"[db] {text}", flush=True)  # live progress: a slow step shows as slow, not stuck


def start(folder: Path, port: int | None = None, database: str = "agentic_qe", say=_say) -> str:
    """Create the cluster if needed, start it, make the database; returns the connection URL.

    A new cluster is made with loopback-only trust, given its random password over SQL, and switched to SCRAM before
    anything else connects. (A password file for initdb fails on Windows: initdb drops to a restricted token that cannot
    read a file the administrator account just wrote.)"""
    import psycopg  # the backend's own driver
    from psycopg import sql

    folder = Path(folder).resolve()
    secret, data = folder / ".atlas-password", folder / "data"
    fresh = not (data / "PG_VERSION").is_file()
    if fresh:
        say(f"Creating a new cluster in {data} (first run only)")
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt" and os.environ.get("USERNAME"):  # initdb drops the Administrators group; the user itself must own the folder
            _run([shutil.which("icacls") or "icacls", str(folder), "/grant", f"{os.environ['USERNAME']}:(OI)(CI)F", "/Q"])
        _run([binary("initdb"), "-D", str(data), "-U", USER, "--auth=trust", "-E", "UTF8", "--locale=C"])
    elif not secret.is_file():
        sys.exit(f"{data} exists but its password file {secret} is missing. Move the folder away to start a new cluster.")
    saved = folder / ".atlas-port"  # a developer cluster keeps its port, so the URL in .env stays right
    if not port:
        port = int(saved.read_text(encoding="utf-8")) if saved.is_file() else free_port()
    saved.write_text(str(port), encoding="utf-8")
    # TCP on loopback only; no Unix socket, whose path has a 103-byte limit a deep app-data folder can exceed (Windows has none by default)
    options = f"-p {port} -c listen_addresses=127.0.0.1" + ("" if os.name == "nt" else " -c unix_socket_directories=''")
    log = folder / "server.log"
    if subprocess.run([binary("pg_ctl"), "-D", str(data), "status"], capture_output=True, timeout=30, check=False, env=_env()).returncode != 0:
        say(f"Starting PostgreSQL on 127.0.0.1:{port} (server log: {log})")
        # no captured pipes: on Windows the server inherits them and keeps them open, so a captured run never returns
        # (found 2026-11-12: `dev.py db` stuck for 10+ minutes). Its output goes to the -l log file instead.
        done = subprocess.run([binary("pg_ctl"), "-D", str(data), "-o", options, "-l", str(log), "-w", "-t", "60", "start"],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False, env=_env())
        if done.returncode:
            tail = log.read_text(encoding="utf-8", errors="replace")[-1500:] if log.is_file() else "(no server log)"
            sys.exit(f"PostgreSQL did not start (pg_ctl exit {done.returncode}). Last lines of {log}:\n{tail}")
    if fresh:
        password = secrets.token_urlsafe(24)
        say("Setting the cluster's random password and switching to password sign-in")
        with psycopg.connect(f"postgresql://{USER}@127.0.0.1:{port}/postgres", autocommit=True, connect_timeout=10) as con:
            con.execute(sql.SQL("ALTER USER {} PASSWORD {}").format(sql.Identifier(USER), sql.Literal(password)))
        hba = data / "pg_hba.conf"
        hba.write_text(hba.read_text(encoding="utf-8").replace(" trust", " scram-sha-256"), encoding="utf-8")
        subprocess.run([binary("pg_ctl"), "-D", str(data), "reload"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60, check=True, env=_env())
        secret.write_text(password, encoding="utf-8")
        os.chmod(secret, 0o600)
    password = secret.read_text(encoding="utf-8").strip()
    admin = f"postgresql://{USER}:{password}@127.0.0.1:{port}/postgres"
    with psycopg.connect(admin, autocommit=True, connect_timeout=10) as con:
        if not con.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    say(f"Ready: database {database} on 127.0.0.1:{port}")
    return f"postgresql://{USER}:{password}@127.0.0.1:{port}/{database}"


def stop(folder: Path) -> None:
    data = Path(folder) / "data"
    if (data / "PG_VERSION").is_file():
        subprocess.run([binary("pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"], capture_output=True, timeout=60, check=False, env=_env())
