"""Reading the span store for the trace explorer, limited in SQL to what the caller may see.

An admin sees every trace. Anyone else sees a trace only when its root span's user_id is theirs and its project, if any,
is one they can see. Any other trace answers KeyError (404), so its existence is not revealed.
"""
from __future__ import annotations

import json

from backend.core import auth
from backend.db import db, rows

LIST_COLUMNS = "r.trace_id, r.name, r.status, r.duration_ms, r.started_at, r.project_id, r.user_id, r.attributes"


def _scope(user: dict) -> tuple[str, dict]:
    if user["role"] == "admin":
        return "", {}
    visible = f"(SELECT id FROM projects WHERE {auth.VISIBLE_PROJECTS} AND id!=:eval)"
    return f" AND r.user_id=:owner AND (r.project_id IS NULL OR r.project_id IN {visible})", {"owner": user["id"], "eval": auth.EVAL_PROJECT}


def _names(items: list[dict]) -> None:
    users = auth.display_names({i["user_id"] for i in items if i["user_id"]})
    ids = sorted({i["project_id"] for i in items if i["project_id"]})
    with db() as con:
        projects = dict(con.execute(f"SELECT id, name FROM projects WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()) if ids else {}
    for item in items:
        item["user"] = users.get(item["user_id"] or "", "")
        item["project"] = projects.get(item["project_id"] or "", "")


def _summary(found: dict) -> dict:
    attributes = json.loads(found.pop("attributes") or "{}")
    return {**found, "agent": attributes.get("agent", ""), "model": attributes.get("model", ""), "tokens_in": attributes.get("tokens_in", 0),
            "tokens_out": attributes.get("tokens_out", 0), "error_id": attributes.get("error_id", "")}


def list_runs(user: dict, *, project: str = "", owner: str = "", agent: str = "", status: str = "", start: str = "", end: str = "", q: str = "",
              requests: bool = False, limit: int = 50, offset: int = 0) -> dict:
    """Root spans, newest first. A plain API request with no child span is left out unless it failed or `requests` is set."""
    scope, params = _scope(user)
    filters = [scope]
    for value, clause, key in ((project, "r.project_id=:project", "project"), (owner, "r.user_id=:user", "user"), (agent, "json_extract(r.attributes,'$.agent')=:agent", "agent"),
                               (status, "r.status=:status", "status"), (start, "r.started_at>=:start", "start"), (end, "r.started_at<=:end", "end")):
        if value:
            filters.append(f" AND {clause}")
            params[key] = value
    if q:
        filters.append(" AND EXISTS (SELECT 1 FROM spans c WHERE c.trace_id=r.trace_id AND instr(lower(c.name||' '||c.attributes), lower(:q))>0)")
        params["q"] = q
    if not requests:
        filters.append(" AND (r.status='error' OR EXISTS (SELECT 1 FROM spans c WHERE c.trace_id=r.trace_id AND c.root=0))")
    where = "".join(filters)
    with db() as con:
        total = con.execute(f"SELECT COUNT(*) FROM spans r WHERE r.root=1{where}", params).fetchone()[0]
        found = rows(con.execute(f"SELECT {LIST_COLUMNS}, (SELECT COUNT(*) FROM spans c WHERE c.trace_id=r.trace_id) AS spans FROM spans r WHERE r.root=1{where}"
                                 " ORDER BY r.started_at DESC, r.span_id LIMIT :n OFFSET :o", {**params, "n": limit, "o": offset}))
    items = [_summary(f) for f in found]
    _names(items)
    return {"items": items, "total": total, "limit": limit, "offset": offset, "scope": "all" if user["role"] == "admin" else "own"}


def get_trace(user: dict, trace_id: str) -> dict:
    """The root and every span of one trace, oldest first. Someone else's trace raises KeyError."""
    scope, params = _scope(user)
    with db() as con:
        root = con.execute(f"SELECT {LIST_COLUMNS}, 0 AS spans FROM spans r WHERE r.root=1 AND r.trace_id=:trace{scope} LIMIT 1", {**params, "trace": trace_id}).fetchone()
        if not root:
            raise KeyError("trace")
        spans = rows(con.execute("SELECT span_id, parent_id, name, kind, started_at, ended_at, duration_ms, status, attributes FROM spans WHERE trace_id=? ORDER BY started_at, span_id", (trace_id,)))
    for span in spans:
        span["attributes"] = json.loads(span["attributes"] or "{}")
    summary = _summary(dict(root))
    summary["spans"] = len(spans)
    _names([summary])
    return {"trace_id": trace_id, "root": summary, "spans": spans}
