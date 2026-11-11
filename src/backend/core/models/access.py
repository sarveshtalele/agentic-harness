"""Who may use which model: the ticks per account and the checks on them."""
from __future__ import annotations

from backend.db import db


def allowed(user_id: str) -> list[str]:
    """Ticked and enabled models. Switching a model off removes it from everyone without losing the ticks."""
    with db() as con:
        return [r[0] for r in con.execute("SELECT m.name FROM user_models u JOIN models m ON m.name=u.model WHERE u.user_id=? AND m.enabled=1 ORDER BY m.name", (user_id,))]


def ticked(user_id: str) -> list[str]:
    with db() as con:
        return [r[0] for r in con.execute("SELECT model FROM user_models WHERE user_id=? ORDER BY model", (user_id,))]


def is_enabled(name: str) -> bool:
    with db() as con:
        found = con.execute("SELECT enabled FROM models WHERE name=?", (name,)).fetchone()
    return bool(found and found[0])


def is_disabled(name: str) -> bool:
    with db() as con:
        found = con.execute("SELECT enabled FROM models WHERE name=?", (name,)).fetchone()
    return bool(found) and not found[0]


def check_allowed(names: list[str], default: str | None) -> str:
    """The default is one of the ticked models: a blank default becomes the first, and a default that is not ticked is refused."""
    names = sorted(set(names))
    with db() as con:
        known = {r[0] for r in con.execute("SELECT name FROM models")}
    if unknown := [n for n in names if n not in known]:
        raise ValueError(f"Not in the model list: {', '.join(unknown)}")
    if default and default not in names:
        raise ValueError("The default model must be one of the ticked models")
    return default or (names[0] if names else "")


def set_allowed(user_id: str, names: list[str], default: str | None) -> str:
    """Replaces the ticks, and drops per-model limits of models no longer ticked. Returns the default to store."""
    default = check_allowed(names, default)
    with db() as con:
        con.execute("DELETE FROM user_models WHERE user_id=?", (user_id,))
        con.executemany("INSERT INTO user_models (user_id, model) VALUES (?,?)", [(user_id, n) for n in sorted(set(names))])
        con.execute("DELETE FROM user_limits WHERE user_id=? AND model<>'' AND model NOT IN (SELECT model FROM user_models WHERE user_id=?)", (user_id, user_id))
    return default
