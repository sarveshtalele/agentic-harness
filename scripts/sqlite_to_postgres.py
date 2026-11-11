#!/usr/bin/env python3
"""Copy an existing SQLite store into PostgreSQL once (MASTER_PLAN Part 3, G5). The SQLite file is only read.

  python scripts/sqlite_to_postgres.py [path/to/atlas.sqlite3]     target: ATLAS_DATABASE_URL (from .env or the environment)

The target is migrated first and must hold no data. Tables are copied in foreign-key order with their own ids; the
`rowid` order columns get SQLite's rowid, and identity sequences continue after the copied ids. Afterwards it checks:
the row count of every table, every project's ledger hash chain (`core/ledger.verify`), and the SHA-256 of every
document version. It prints table names and counts only, never values. This is the one code path that still reads
SQLite, and it goes once the owner has moved the data.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from backend import db as database  # noqa: E402
from backend.config import DATA_DIR  # noqa: E402
from backend.core import ledger  # noqa: E402
from backend.core.security import sha256  # noqa: E402

ORDERED = ("run_events", "ledger", "evaluations", "run_failures")  # PostgreSQL keeps SQLite's rowid in a `rowid` column


def _tables(con) -> list[str]:
    """Every table in foreign-key order (a table after the ones it references)."""
    names = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() AND table_name<>'schema_migrations'")]
    needs = {n: set() for n in names}
    for child, parent in con.execute("SELECT tc.table_name, ccu.table_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage ccu "
                                     "ON tc.constraint_name=ccu.constraint_name WHERE tc.constraint_type='FOREIGN KEY'"):
        if child != parent:
            needs[child].add(parent)
    ordered: list[str] = []
    while needs:
        ready = sorted(n for n, deps in needs.items() if deps <= set(ordered))
        if not ready:
            sys.exit(f"Foreign keys form a cycle among {sorted(needs)}")
        ordered += ready
        for n in ready:
            needs.pop(n)
    return ordered


def _columns(con, table: str) -> list[str]:
    return [r[0] for r in con.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=? ORDER BY ordinal_position", (table,))]


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / "atlas.sqlite3"
    if not source.is_file():
        sys.exit(f"No SQLite store at {source}")
    old = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    old.row_factory = sqlite3.Row
    present = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    database.migrate()
    counts = {}
    with database.db() as con:
        tables = _tables(con)
        if any(con.execute(f'SELECT 1 FROM "{t}" LIMIT 1').fetchone() for t in tables):
            sys.exit("The PostgreSQL database already holds data. Use an empty database.")
        for table in tables:
            if table not in present:
                counts[table] = (0, 0)
                continue
            wanted = _columns(con, table)
            have = [c for c in wanted if c in {r[1] for r in old.execute(f'PRAGMA table_info("{table}")')}]
            pick = have + (["rowid"] if table in ORDERED else [])
            got = old.execute(f'SELECT {", ".join(pick)} FROM "{table}"').fetchall()
            if got:
                marks = ", ".join(["%s"] * len(pick))
                with con.raw.cursor() as cur:  # psycopg directly: these statements are PostgreSQL already
                    cur.executemany(f'INSERT INTO "{table}" ({", ".join(pick)}) OVERRIDING SYSTEM VALUE VALUES ({marks})', [tuple(r) for r in got])
            for column in [r[0] for r in con.raw.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s AND is_identity='YES'", (table,))]:
                con.raw.execute(f"SELECT setval(pg_get_serial_sequence(%s, %s), GREATEST((SELECT MAX({column}) FROM \"{table}\"), 1))", (table, column))
            counts[table] = (len(got), con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    bad = {t: c for t, c in counts.items() if c[0] != c[1]}
    for table, (copied, now_there) in counts.items():
        print(f"{table}: {copied} copied, {now_there} in PostgreSQL")
    with database.db() as con:
        projects = [r[0] for r in con.execute("SELECT id FROM projects")]
        versions = con.execute("SELECT document_id, version, content, sha256 FROM document_versions").fetchall()
    broken = [p for p in projects if not ledger.verify(p)["valid"]]
    wrong = [f"{v[0]} v{v[1]}" for v in versions if sha256(v[2]) != v[3]]  # the same digest documents.save stores
    print(f"Ledger chains: {len(projects) - len(broken)} of {len(projects)} verify. Document versions: {len(versions) - len(wrong)} of {len(versions)} match their SHA-256.")
    if bad or broken or wrong:
        print(f"PROBLEMS: counts {bad}, ledgers {broken}, documents {wrong[:20]}")
        return 1
    print("Copy complete and verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
