"""PostgreSQL access (MASTER_PLAN Part 3, G5): one pooled connection per unit of work, numbered SQL migrations.

`ATLAS_DATABASE_URL` is required; a missing or unreachable database stops the app with a clear message. Rows work like
`sqlite3.Row` (by name and by position, and `dict(row)`). The SQL in the modules is plain SQL with `?` or `:name`
placeholders; `backend/sql_dialect.py` turns those and the few SQLite idioms left (`INSERT OR IGNORE`, `BEGIN IMMEDIATE`,
`LIKE`, `json_extract`) into PostgreSQL, once per statement text.
"""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.adapt import Dumper
from psycopg_pool import ConnectionPool

from backend import sql_dialect
from backend.config import DATABASE_URL, DB_POOL_SIZE

MIGRATIONS = Path(__file__).parent / "migrations" / "postgres"
_pool: ConnectionPool | None = None
_lock = threading.Lock()


class DatabaseNotConfigured(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Row(tuple):
    """A result row read by column name or position, like sqlite3.Row."""

    def __new__(cls, names: list[str], values):
        made = super().__new__(cls, values)
        made._names = names
        return made

    def __getitem__(self, key):
        return super().__getitem__(self._names.index(key) if isinstance(key, str) else key)

    def keys(self) -> list[str]:
        return list(self._names)


def _rows(cursor):
    names = [c.name for c in cursor.description or []]
    return lambda values: Row(names, values)


class _BoolAsInt(Dumper):  # the schema keeps SQLite's 0/1 integer flags, so Python booleans go in as integers
    oid = psycopg.postgres.types["int8"].oid

    def dump(self, obj):
        return b"1" if obj else b"0"


def _configure(con: psycopg.Connection) -> None:
    con.adapters.register_dumper(bool, _BoolAsInt)


def pool() -> ConnectionPool:
    global _pool
    with _lock:
        if _pool is None:
            if not DATABASE_URL:
                raise DatabaseNotConfigured("ATLAS_DATABASE_URL is not set. Locally run `python scripts/dev.py db` and put the URL it prints in .env; "
                                            "on Azure it comes from Key Vault (atlas-database-url).")
            _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=DB_POOL_SIZE, kwargs={"row_factory": _rows}, configure=_configure, open=False)
            _pool.open(wait=True, timeout=30)
        return _pool


class Connection:
    """What `with db() as con` gives: `execute`/`executemany` in the shared SQL dialect, inside one transaction."""

    def __init__(self, con: psycopg.Connection):
        self.raw = con

    def execute(self, sql: str, params=()):
        text, args = sql_dialect.translate(sql, params, self._primary_key)
        return self.raw.execute(text, args)

    def executemany(self, sql: str, seq):
        """Returns the cursor, so `.rowcount` counts the rows every statement touched."""
        items = list(seq)
        cur = self.raw.cursor()
        if items:
            text, _ = sql_dialect.translate(sql, items[0], self._primary_key)
            cur.executemany(text, [sql_dialect.translate(sql, p, self._primary_key)[1] for p in items])
        return cur

    def cursor(self):  # code written for sqlite3 asks for a cursor; this connection executes directly
        return self

    def _primary_key(self, table: str) -> list[str]:
        return sql_dialect.primary_key(self.raw, table)


@contextmanager
def db() -> Iterator[Connection]:
    """One transaction: committed when the block ends, rolled back when it raises."""
    with pool().connection() as con:
        yield Connection(con)


def rows(cursor) -> list[dict]:
    return [dict(zip(r.keys(), r)) for r in cursor.fetchall()]


def row(cursor) -> dict | None:
    found = cursor.fetchone()
    return dict(zip(found.keys(), found)) if found else None


def migrate() -> None:
    """Apply `migrations/postgres/NNNN_*.sql` not yet applied, in order, under an advisory lock (one migrator at a time)."""
    with pool().connection() as con:
        con.execute("SELECT pg_advisory_xact_lock(7300001)")
        con.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version BIGINT PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        done = {r[0] for r in con.execute("SELECT version FROM schema_migrations").fetchall()}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            number = int(path.name.split("_")[0])
            if number not in done:
                con.execute(path.read_text(encoding="utf-8"))
                con.execute("INSERT INTO schema_migrations (version, name, applied_at) VALUES (%s, %s, %s)", (number, path.name, now()))


def close() -> None:
    global _pool
    with _lock:
        if _pool is not None:
            _pool.close()
            _pool = None
