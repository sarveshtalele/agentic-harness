"""The registry tables: a sync replaces every row in one transaction and records the hash of the whole table."""
from __future__ import annotations

import json
import sqlite3

from backend.core.registry.model import Graph, digest
from backend.db import db, now, row, rows

COLUMNS = ("id", "kind", "name", "qualified_name", "description", "when_to_use", "source", "plugin", "sha256", "risk",
           "needs_approval", "profiles", "enabled", "meta")


def _row(cid: str, cap) -> tuple:
    return (cid, cap.kind, cap.name, cap.qualified_name, cap.description, cap.when_to_use, cap.source, cap.plugin, cap.sha256, cap.risk,
            int(cap.needs_approval), cap.profiles, int(cap.enabled), json.dumps(cap.meta, sort_keys=True, default=str))


def table_hash(capability_rows: list[tuple], links: list[tuple]) -> str:
    """Everything but updated_at, sorted, so the same sources always give the same hash."""
    return digest(json.dumps([sorted(capability_rows), sorted(links)], default=str))


def write(g: Graph, by: str, problems: list[str]) -> dict:
    capability_rows = [_row(cid, cap) for cid, cap in g.caps.items()]
    links = sorted(g.links)
    version = table_hash(capability_rows, links)
    stamp = now()
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        before = {r[0]: (r[1], r[2]) for r in con.execute("SELECT id, sha256, updated_at FROM capabilities")}
        con.execute("DELETE FROM capability_links")
        con.execute("DELETE FROM capabilities")
        con.executemany(f"INSERT INTO capabilities ({', '.join(COLUMNS)}, updated_at) VALUES ({', '.join('?' * (len(COLUMNS) + 1))})",
                        [(*r, before[r[0]][1] if before.get(r[0], ("",))[0] == r[8] else stamp) for r in capability_rows])
        con.executemany("INSERT INTO capability_links (from_id, to_id, relation, detail) VALUES (?,?,?,?)", links)
        con.execute("INSERT INTO registry_versions (hash, capabilities, links, problems, synced_by, synced_at) VALUES (?,?,?,?,?,?)",
                    (version, len(capability_rows), len(links), json.dumps(problems), by, stamp))
    return latest()


def latest() -> dict | None:
    try:
        with db() as con:
            found = row(con.execute("SELECT * FROM registry_versions ORDER BY id DESC LIMIT 1"))
    except sqlite3.OperationalError:  # before migration 023
        return None
    if found:
        found["problems"] = json.loads(found["problems"])
    return found


def capabilities() -> list[dict]:
    with db() as con:
        found = rows(con.execute("SELECT * FROM capabilities ORDER BY kind, qualified_name"))
    for item in found:
        item["meta"] = json.loads(item["meta"])
        item["needs_approval"], item["enabled"] = bool(item["needs_approval"]), bool(item["enabled"])
    return found


def links() -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT * FROM capability_links ORDER BY relation, from_id, to_id, detail"))
