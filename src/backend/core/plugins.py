"""Plugin discovery: `plugins/*/` folders plus the repo's own `skills/` as the implicit plugin "local-skills".

A manifest is our `plugin.json`, the Claude Code `.claude-plugin/plugin.json`, or a root `plugin.json` in agents format.
Plugin text is trusted platform content (first-party, in this repo). Every manifest path goes through `safe_path`.
A plugin's `.mcp.json` (Claude Code format) declares MCP servers; an admin registers them. A disabled plugin's skills and
commands leave `skill_paths()` and `slash_entries()`, and so do an ungranted plugin's for that role.
"""
from __future__ import annotations

import json
import psycopg
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend.config import ROOT, SKILLS_DIR
from backend.core import auth, plugin_grants
from backend.core.security import PathEscape, safe_path
from backend.db import db, now

MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")


@dataclass(frozen=True)
class Plugin:
    id: str
    version: str
    description: str
    trust: str
    source: str
    root: Path
    skills_dir: Path | None
    manifest: str  # relative to root, "" when implicit
    problems: list[str] = field(default_factory=list)
    enabled: bool = True
    mcp_servers: list[dict] = field(default_factory=list)  # from .mcp.json: name, transport, command, args, env, url, headers


def _mcp_servers(folder: Path) -> tuple[list[dict], list[str]]:
    """Servers a plugin's `.mcp.json` declares: {"mcpServers": {name: {command, args, env} | {url, headers}}}."""
    if not (folder / ".mcp.json").is_file():
        return [], []
    try:
        data = json.loads(safe_path(folder, ".mcp.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, PathEscape) as exc:
        return [], [f".mcp.json: {exc}"]
    declared = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(declared, dict):
        return [], [".mcp.json: mcpServers must be an object"]
    found, problems = [], []
    for name, spec in declared.items():
        if not isinstance(spec, dict) or not (spec.get("command") or spec.get("url")) or spec.get("type") == "sse":
            problems.append(f".mcp.json: {name} needs a command, or a url for streamable HTTP (sse is not supported)")
            continue
        transport = "stdio" if spec.get("command") else "websocket" if str(spec["url"]).startswith(("ws://", "wss://")) else "http"
        found.append({"name": str(name), "transport": transport, "command": spec.get("command"), "args": spec.get("args") or [],
                      "env": spec.get("env"), "url": spec.get("url"), "headers": spec.get("headers")})
    return found, problems


def _enabled() -> dict[str, bool]:
    try:
        with db() as con:
            return {r[0]: bool(r[1]) for r in con.execute("SELECT plugin_id, enabled FROM plugin_state")}
    except psycopg.errors.UndefinedTable:  # before plugin_state exists, every plugin was enabled
        return {}


def set_enabled(plugin_id: str, enabled: bool, by: str, root: Path | None = None) -> None:
    if plugin_id not in {p.id for p in discover(root)}:
        raise KeyError(f"plugin {plugin_id}")
    if plugin_id == "local-skills":
        raise ValueError("The repository's own skills/ folder cannot be disabled")
    with db() as con:
        con.execute("INSERT OR REPLACE INTO plugin_state (plugin_id, enabled, updated_by, updated_at) VALUES (?,?,?,?)", (plugin_id, int(enabled), by, now()))


def _read_manifest(folder: Path) -> tuple[str, dict, list[str]]:
    for rel in MANIFESTS:
        path = folder / rel
        if path.is_file():
            try:
                data = json.loads(safe_path(folder, rel).read_text(encoding="utf-8"))
            except (OSError, ValueError, PathEscape) as exc:
                return rel, {}, [f"{rel}: {exc}"]
            return (rel, data, []) if isinstance(data, dict) else (rel, {}, [f"{rel}: must be a JSON object"])
    return "", {}, ["no manifest"]


def _plugin(folder: Path, enabled: dict[str, bool] | None = None) -> Plugin:
    rel, data, problems = _read_manifest(folder)
    servers, mcp_problems = _mcp_servers(folder)
    problems += mcp_problems
    skills_rel = data.get("skills", "skills/")
    skills_dir: Path | None = None
    if not isinstance(skills_rel, str):
        problems.append("skills must be a relative folder name")
    else:
        try:
            found = safe_path(folder, skills_rel)
            skills_dir = found if found.is_dir() else None
            if skills_dir is None:
                problems.append(f"skills folder not found: {skills_rel}")
        except PathEscape:
            problems.append(f"skills path escapes the plugin folder: {skills_rel}")
    plugin_id = str(data.get("id") or data.get("name") or folder.name)
    return Plugin(plugin_id, str(data.get("version", "")), str(data.get("description", "")), "first-party", "repo", folder, skills_dir, rel, problems,
                  (enabled or {}).get(plugin_id, True), servers)


def discover(root: Path | None = None) -> list[Plugin]:
    # ponytail: rescans per call; cache with mtime if it gets slow
    base = (root or ROOT).resolve()
    local = Plugin("local-skills", "", "Skills in the repository skills/ folder", "first-party", "repo", SKILLS_DIR.parent,
                   SKILLS_DIR if SKILLS_DIR.is_dir() else None, "", [] if SKILLS_DIR.is_dir() else ["skills folder not found"])
    folders = sorted(p for p in (base / "plugins").glob("*") if p.is_dir()) if (base / "plugins").is_dir() else []
    state = _enabled()
    return [local, *(_plugin(p, state) for p in folders)]


def _split(skill_md: Path) -> tuple[dict, str]:
    """Frontmatter and body of a SKILL.md, read raw (MAF drops fields such as `disable-model-invocation`)."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---") or "\n---" not in text:
        return {}, text
    head, body = text[3:].split("\n---", 1)
    try:
        front = yaml.safe_load(head)
    except yaml.YAMLError:
        return {}, text
    return (front, body.lstrip("-\n")) if isinstance(front, dict) else ({}, text)


def command_skill_names(skills_dir: Path) -> set[str]:
    """Skill folders whose SKILL.md frontmatter sets `disable-model-invocation: true` (slash commands)."""
    names: set[str] = set()
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        front, _ = _split(skill_md)
        if front.get("disable-model-invocation") is True:
            names.add(str(front.get("name") or skill_md.parent.name))
    return names


def slash_entries(root: Path | None = None, role: str | None = None) -> list[dict]:
    """What the chat "/" menu offers: plugin commands as `/plugin:name`, every other skill as `/name`. With `role`, only
    the plugins that role was granted (core/plugin_grants.py); None means no filter, for callers without a user."""
    entries: list[dict] = []
    granted = plugin_grants.allowed(role)
    for plugin in (p for p in discover(root) if p.enabled and granted(p.id)):
        for skill_md in sorted(plugin.skills_dir.glob("*/SKILL.md")) if plugin.skills_dir else []:
            front, _ = _split(skill_md)
            name = str(front.get("name") or skill_md.parent.name)
            command = front.get("disable-model-invocation") is True
            entries.append({"name": f"{plugin.id}:{name}" if command else name, "kind": "command" if command else "skill", "plugin": plugin.id,
                            "description": " ".join(str(front.get("description", "")).split())[:240],
                            "argument_hint": str(front.get("argument-hint", "")), "path": skill_md})
    return entries


def expand_slash(text: str, root: Path | None = None) -> str | None:
    """`/plugin:command args` becomes that command's instructions with $ARGUMENTS filled in; `/skill args` asks the
    harness to load that skill. Anything else, including an unknown name, returns None and the text goes as typed."""
    head, _, args = text.strip().partition(" ")
    if not head.startswith("/") or len(head) < 2:
        return None
    wanted, args = head[1:], args.strip()
    entries = slash_entries(root, plugin_grants.role_of(auth.current_user.get()))  # an ungranted command does not expand
    found = next((e for e in entries if e["name"] == wanted), None) or next(
        (e for e in entries if e["kind"] == "command" and e["name"].split(":", 1)[1] == wanted), None)
    if not found:
        return None
    if found["kind"] == "skill":
        return f"Load the skill {found['name']} with load_skill, then use it for this request: {args or 'the current project'}"
    _, body = _split(found["path"])
    body = body.replace("$ARGUMENTS", args) if "$ARGUMENTS" in body else f"{body}\n\nARGUMENTS: {args}"
    # Claude Code's own variables in plugin commands, filled the way Claude Code fills them (the model writes these paths in shell commands)
    plugin_root = next((p.root for p in discover(root) if p.id == found["plugin"]), None)
    body = body.replace("${CLAUDE_SKILL_DIR}", str(found["path"].parent)).replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root or found["path"].parent))
    return (f"The user ran the command /{found['name']} {args}".rstrip() + ". Carry out its instructions below with the tools you have: do its steps in order, "
            "stop where it says to wait for the user, and do nothing it does not ask for. "
            "Where a step needs a tool or script you do not have here, say so plainly instead of claiming it ran.\n\n"
            f"<command name=\"{found['name']}\">\n{body.strip()}\n</command>")


def skill_paths(root: Path | None = None, role: str | None = None) -> list[Path]:
    """Skill folders of enabled plugins; with `role`, only plugins that role was granted. None means no filter."""
    seen: list[Path] = []
    granted = plugin_grants.allowed(role)
    for plugin in discover(root):
        if plugin.enabled and granted(plugin.id) and plugin.skills_dir and plugin.skills_dir not in seen:
            seen.append(plugin.skills_dir)
    return seen
