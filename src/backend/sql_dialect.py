"""The platform's SQL text, made PostgreSQL (MASTER_PLAN Part 3, G5).

Modules write `?` or `:name` placeholders, as they did on SQLite. Outside string literals this turns:
- `?` into `%s` and `:name` into `%(name)s` (a `::cast` is left alone), and a literal `%` into `%%`;
- `INSERT OR IGNORE` into `INSERT … ON CONFLICT DO NOTHING`, and `INSERT OR REPLACE` into an upsert on the primary key;
- `BEGIN IMMEDIATE` into a transaction-wide advisory lock: the same one-writer-at-a-time order SQLite's write lock gave
  (ponytail: one global lock for those few read-then-write blocks; per-table locks if they ever contend);
- `LIKE` into `ILIKE` (SQLite's LIKE ignores ASCII case), `IFNULL` into `COALESCE`, `instr` into `strpos`, `SUM(a=b)` into a 0/1 sum, and
  `json_extract(x, '$.key')` into `(x::jsonb ->> 'key')`.
Each distinct statement text is translated once and cached.
"""
from __future__ import annotations

import re
from functools import lru_cache

LITERAL = re.compile(r"('(?:[^']|'')*')")
NAMED = re.compile(r"(?<![:\w]):([A-Za-z_]\w*)")
INSERT_INTO = re.compile(r"^\s*INSERT\s+OR\s+(IGNORE|REPLACE)\s+INTO\s+(\w+)\s*(?:\(([^)]*)\))?", re.I | re.S)
JSON_EXTRACT = re.compile(r"json_extract\(\s*([\w.]+)\s*,\s*'\$\.(\w+)'\s*\)", re.I)
WORDS = [(re.compile(r"\bNOT\s+LIKE\b", re.I), "NOT ILIKE"), (re.compile(r"(?<!NOT )\bLIKE\b", re.I), "ILIKE"),
         (re.compile(r"\bIFNULL\s*\(", re.I), "COALESCE("), (re.compile(r"\binstr\s*\(", re.I), "strpos(")]
BOOL_SUM = re.compile(r"\bSUM\(([^()]*?(?:=|<>|!=|<|>|\sIN\s|\sIS\s)[^()]*)\)", re.I)  # SQLite sums a comparison as 0/1
LOCK = "SELECT pg_advisory_xact_lock(7300002)"
_keys: dict[str, tuple[list[str], list[str]]] = {}


@lru_cache(maxsize=4096)
def _text(sql: str, named: bool) -> tuple[str, str, str, tuple[str, ...]]:
    """(PostgreSQL text, OR-mode, table, columns) for one statement text."""
    if re.fullmatch(r"\s*BEGIN\s+IMMEDIATE\s*;?\s*", sql, re.I):
        return LOCK, "", "", ()
    mode, table, columns = "", "", ()
    found = INSERT_INTO.match(sql)
    if found:
        mode, table, columns = found[1].upper(), found[2], tuple(c.strip() for c in (found[3] or "").split(",") if c.strip())
        sql = re.sub(r"^\s*INSERT\s+OR\s+(IGNORE|REPLACE)\s+INTO", "INSERT INTO", sql, count=1, flags=re.I)
    parts = LITERAL.split(sql)
    for i, part in enumerate(parts):
        part = part.replace("%", "%%")  # psycopg reads % anywhere in a statement that has parameters
        if i % 2 == 0:  # outside string literals
            part = NAMED.sub(r"%(\1)s", part) if named else part.replace("?", "%s")
            for pattern, repl in WORDS:
                part = pattern.sub(repl, part)
        parts[i] = part
    text = BOOL_SUM.sub(r"SUM(CASE WHEN \1 THEN 1 ELSE 0 END)", "".join(parts))  # on the whole text: the comparison may hold a literal
    return JSON_EXTRACT.sub(r"(\1::jsonb ->> '\2')", text), mode, table, columns


def translate(sql: str, params, primary_key) -> tuple[str, object]:
    named = isinstance(params, dict)
    text, mode, table, columns = _text(sql, named)
    if mode == "IGNORE":
        text = text.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    elif mode == "REPLACE":
        keys, every = primary_key(table)
        rest = [c for c in (columns or every) if c not in keys]  # no column list: every column of the table, in order
        update = ", ".join(f"{c}=EXCLUDED.{c}" for c in rest) if rest else None
        text = text.rstrip().rstrip(";") + f" ON CONFLICT ({', '.join(keys)}) " + (f"DO UPDATE SET {update}" if update else "DO NOTHING")
    return text, (params if named else tuple(params or ()))


def primary_key(con, table: str) -> tuple[list[str], list[str]]:
    """(primary key columns, every column in order) of a table, read once from the catalogue."""
    if table not in _keys:
        keys = con.execute(
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = %s::regclass AND i.indisprimary ORDER BY array_position(i.indkey, a.attnum)", (table,)).fetchall()
        if not keys:
            raise ValueError(f"INSERT OR REPLACE needs a primary key on {table}")
        every = con.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = current_schema() "
                            "AND is_identity = 'NO' ORDER BY ordinal_position", (table,)).fetchall()
        _keys[table] = ([r[0] for r in keys], [r[0] for r in every])
    return _keys[table]
