"""The model list: names, labels, the default, per-agent models, tool checks, and the config seed."""
from __future__ import annotations

from backend.db import db, now, row, rows


def list_models() -> list[dict]:
    with db() as con:
        return [{**m, "enabled": bool(m["enabled"]), "is_default": bool(m["is_default"])} for m in rows(con.execute("SELECT * FROM models ORDER BY name"))]


def add(name: str, label: str = "", enabled: bool = False) -> dict:
    name = name.strip()
    if not name or name == "*" or len(name) > 200:
        raise ValueError("A model needs a real name. The * wildcard is not a model")
    with db() as con:
        con.execute("INSERT OR IGNORE INTO models (name, label, enabled, is_default, created_at) VALUES (?,?,?,0,?)", (name, label.strip() or name, int(enabled), now()))
    return get(name)


def get(name: str) -> dict:
    with db() as con:
        found = row(con.execute("SELECT * FROM models WHERE name=?", (name,)))
    if not found:
        raise KeyError(name)
    return {**found, "enabled": bool(found["enabled"]), "is_default": bool(found["is_default"])}


def update(name: str, changes: dict) -> dict:
    """A new model starts switched off: being listed does not mean it works. Only an enabled model can be the default."""
    current = get(name)
    enabled = bool(changes.get("enabled", current["enabled"]))
    default = bool(changes.get("is_default", current["is_default"]))
    if default and not enabled:
        raise ValueError("The default model must be enabled")
    with db() as con:
        if default:
            con.execute("UPDATE models SET is_default=0")
        con.execute("UPDATE models SET label=?, enabled=?, is_default=? WHERE name=?", (changes.get("label", current["label"]).strip() or name, int(enabled), int(default), name))
    return get(name)


def remove(name: str) -> None:
    with db() as con:
        users = [r[0] for r in con.execute("SELECT user_id FROM user_models WHERE model=?", (name,))]
        if users:
            raise ValueError(f"{len(users)} user(s) may still use {name}. Untick it for them first")
        con.execute("DELETE FROM models WHERE name=?", (name,))
        con.execute("DELETE FROM user_limits WHERE model=?", (name,))
        con.execute("UPDATE agent_settings SET model='' WHERE model=?", (name,))


def system_default(configured: str = "") -> str:
    with db() as con:
        found = con.execute("SELECT name FROM models WHERE is_default=1 AND enabled=1").fetchone()
    return found[0] if found else configured


def agent_model(agent: str) -> str:
    with db() as con:
        found = con.execute("SELECT model FROM agent_settings WHERE agent=?", (agent,)).fetchone()
    return found[0] if found else ""


def set_tool_check(name: str, passed: bool, reason: str, max_tokens: int) -> dict:
    """The result of the live tool check, kept on the model row with its time. `reason` is why it failed, or what was seen when it passed."""
    get(name)
    with db() as con:
        con.execute("UPDATE models SET tools_status=?, tools_reason=?, tools_checked_at=?, tools_max_tokens=? WHERE name=?", ("passed" if passed else "failed", reason[:500], now(), max_tokens, name))
    return get(name)


def tool_status(name: str) -> str:
    """'passed', 'failed', or '' when this model was never checked (or is not in the list)."""
    with db() as con:
        found = con.execute("SELECT tools_status FROM models WHERE name=?", (name,)).fetchone()
    return found[0] if found else ""


def tool_checks() -> dict[str, dict]:
    with db() as con:
        return {r["name"]: {"status": r["tools_status"], "reason": r["tools_reason"], "checked_at": r["tools_checked_at"], "max_tokens": r["tools_max_tokens"]}
                for r in rows(con.execute("SELECT name, tools_status, tools_reason, tools_checked_at, tools_max_tokens FROM models"))}


def seed_from_config(configured: str) -> None:
    """A setup that has its model only in .env gets it as the default once, and its users keep access (as migration 009 does for saved settings)."""
    if not configured:
        return
    with db() as con:
        if con.execute("SELECT 1 FROM models WHERE is_default=1").fetchone():
            return
        con.execute("INSERT OR IGNORE INTO models (name, label, enabled, is_default, created_at) VALUES (?,?,1,0,?)", (configured, configured, now()))
        con.execute("UPDATE models SET is_default=1, enabled=1 WHERE name=?", (configured,))
        con.execute("INSERT OR IGNORE INTO user_models (user_id, model) SELECT id, ? FROM users WHERE id NOT IN (SELECT user_id FROM user_models)", (configured,))
