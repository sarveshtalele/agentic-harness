"""PostgreSQL helpers for tests: every table's rows (to prove a secret reached none) and a fresh empty database."""
from __future__ import annotations

import json
import os
import secrets
from contextlib import contextmanager

import psycopg

from backend import db as database


def every_table() -> list[str]:
    with database.db() as con:
        return [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema() ORDER BY table_name")]


def dump() -> str:
    """Every row of every table as one JSON text."""
    with database.db() as con:
        return json.dumps({t: database.rows(con.execute(f'SELECT * FROM "{t}"')) for t in every_table()}, default=str)


@contextmanager
def fresh_database():
    """A new empty, migrated database for the block; the session's database is back afterwards."""
    base = os.environ["ATLAS_DATABASE_URL"]
    server, name = base.rsplit("/", 1)[0], f"t_{secrets.token_hex(6)}"
    with psycopg.connect(f"{server}/postgres", autocommit=True) as con:
        con.execute(f'CREATE DATABASE "{name}"')
    saved = database._pool, database.DATABASE_URL
    database._pool, database.DATABASE_URL = None, f"{server}/{name}"
    try:
        database.migrate()
        yield
    finally:
        database.close()
        database._pool, database.DATABASE_URL = saved
        with psycopg.connect(f"{server}/postgres", autocommit=True) as con:
            con.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
