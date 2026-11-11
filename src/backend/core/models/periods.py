"""Token limits per period, the admin time zone, and the usage report. Periods follow one time zone."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.core.errors import LimitReached
from backend.db import db, rows

DEFAULT_TZ = "Asia/Kolkata"
PERIODS = ("day", "week", "month")
NAMES = {"day": "daily", "week": "weekly", "month": "monthly"}
clock = lambda: datetime.now(timezone.utc)  # noqa: E731 - test seam: tests replace it to move past a reset


def timezone_name() -> str:
    with db() as con:
        found = con.execute("SELECT value FROM settings WHERE key='timezone'").fetchone()
    return found[0] if found and found[0] else DEFAULT_TZ


def set_timezone(name: str) -> str:
    name = name.strip()
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"Unknown time zone {name}. Use a name such as Asia/Kolkata or Europe/London") from exc
    with db() as con:
        con.execute("INSERT OR REPLACE INTO settings VALUES ('timezone', ?)", (name,))
    return name


def bounds(period: str, at: datetime | None = None) -> tuple[str, datetime]:
    """The start of the current period as the UTC string stored in `agent_calls.created_at`, and the moment it resets."""
    zone = ZoneInfo(timezone_name())
    local = (at or clock()).astimezone(zone)
    midnight = datetime(local.year, local.month, local.day, tzinfo=zone)
    if period == "day":
        start, end = midnight, datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), zone)
    elif period == "week":
        monday = local.date() - timedelta(days=local.weekday())
        start, end = datetime.combine(monday, datetime.min.time(), zone), datetime.combine(monday + timedelta(days=7), datetime.min.time(), zone)
    else:
        following = datetime(local.year + (local.month == 12), local.month % 12 + 1, 1, tzinfo=zone)
        start, end = midnight.replace(day=1), following
    return start.astimezone(timezone.utc).isoformat(timespec="seconds"), end


def used(user_id: str, since: str | None = None, model: str = "") -> int:
    sql, args = "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM agent_calls WHERE user_id=?", [user_id]
    if since:
        sql, args = sql + " AND created_at>=?", args + [since]
    if model:
        sql, args = sql + " AND model=?", args + [model]
    with db() as con:
        return con.execute(sql, args).fetchone()[0]


def limits(user_id: str) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT model, period, tokens FROM user_limits WHERE user_id=? ORDER BY model, period", (user_id,)))


def set_limits(user_id: str, overall: dict | None = None, per_model: list[dict] | None = None) -> None:
    """`overall` is {day, week, month}: a number sets, null clears, a missing period stays. `per_model` replaces all per-model limits."""
    with db() as con:
        for period, tokens in (overall or {}).items():
            if period not in PERIODS:
                raise ValueError(f"Unknown period {period}")
            if tokens is None:
                con.execute("DELETE FROM user_limits WHERE user_id=? AND model='' AND period=?", (user_id, period))
            else:
                con.execute("INSERT OR REPLACE INTO user_limits (user_id, model, period, tokens) VALUES (?,'',?,?)", (user_id, period, int(tokens)))
        if per_model is not None:
            ticked_now = {r[0] for r in con.execute("SELECT model FROM user_models WHERE user_id=?", (user_id,))}
            con.execute("DELETE FROM user_limits WHERE user_id=? AND model<>''", (user_id,))
            for item in per_model:
                if item["period"] not in PERIODS or item["model"] not in ticked_now:
                    raise ValueError(f"A per-model limit needs a ticked model and a period of day, week, or month ({item['model']})")
                con.execute("INSERT OR REPLACE INTO user_limits (user_id, model, period, tokens) VALUES (?,?,?,?)", (user_id, item["model"], item["period"], int(item["tokens"])))


def usage(user_id: str) -> dict:
    """Used and limit for each period, for the Users page and the header. `remaining_today` is the tightest all-model daily figure, else None."""
    out = {}
    for period in PERIODS:
        start, reset = bounds(period)
        out[period] = {"used": used(user_id, start), "limit": None, "resets_at": reset.isoformat(timespec="seconds")}
    for item in limits(user_id):
        if not item["model"]:
            out[item["period"]]["limit"] = item["tokens"]
    return out


def limit_problem(user_id: str, model: str = "") -> LimitReached | None:
    """The first limit this user has reached for a call to `model`: an all-model limit, or one set for this model."""
    for item in limits(user_id):
        if item["model"] and item["model"] != model:
            continue
        start, reset = bounds(item["period"])
        total = used(user_id, start, item["model"])
        if total >= item["tokens"]:
            scope = f" on {item['model']}" if item["model"] else ""
            when = reset.strftime("%Y-%m-%d %H:%M") + " " + reset.tzname()
            return LimitReached(f"The {NAMES[item['period']]} limit of {item['tokens']:,} tokens{scope} is reached ({total:,} used). It resets at {when}.", limit=item["period"], model=item["model"], resets_at=reset.isoformat(timespec="seconds"))
    return None


# ---- the admin usage report ------------------------------------------------------

def usage_rows(days: int = 30) -> list[dict]:
    """Tokens by local day, account, model, and agent for the last `days` days, read from recorded calls.

    SQL groups by the minute (the index on created_at limits the scan); local days are made here, because only the zone rules know where a day starts.
    """
    zone = ZoneInfo(timezone_name())
    first = datetime.combine((clock().astimezone(zone) - timedelta(days=days - 1)).date(), datetime.min.time(), zone).astimezone(timezone.utc).isoformat(timespec="seconds")
    with db() as con:
        found = rows(con.execute(
            """SELECT substr(created_at, 1, 16) AS minute, user_id, model, agent, COUNT(*) AS calls, SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out
               FROM agent_calls WHERE created_at >= ? GROUP BY minute, user_id, model, agent""", (first,)))
    merged: dict[tuple, dict] = {}
    for item in found:
        day = datetime.fromisoformat(item["minute"] + ":00+00:00").astimezone(zone).date().isoformat()
        key = (day, item["user_id"] or "", item["model"], item["agent"])
        slot = merged.setdefault(key, {"day": day, "user_id": key[1], "model": key[2], "agent": key[3], "calls": 0, "tokens_in": 0, "tokens_out": 0})
        slot["calls"] += item["calls"]
        slot["tokens_in"] += item["tokens_in"] or 0
        slot["tokens_out"] += item["tokens_out"] or 0
    return sorted(merged.values(), key=lambda r: (r["day"], r["user_id"], r["model"], r["agent"]))
