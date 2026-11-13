"""Registry sources in plugins and the MCP registry: manifests, skills and commands, the scripts their SKILL.md names,
`agents/*.md`, `hooks/hooks.json`, `.mcp.json`, and the MCP servers with the tools their real `list_tools` returned.

Every plugin is read, enabled or not and granted or not; who may see what is decided when the registry is read.
"""
from __future__ import annotations

import json
import re

from backend.core import plugin_hooks, plugins
from backend.core.mcp import registry as mcp
from backend.core.registry.model import ALL_PROFILES, Cap, Graph, digest, one_line, rel
from backend.core.security import PathEscape, safe_path

# `scripts/x.ts`, `${CLAUDE_SKILL_DIR}/scripts/x.ts`, `${CLAUDE_SKILL_DIR}/../other/scripts/x.ts`, `${CLAUDE_PLUGIN_ROOT}/scripts/x.ts`
SCRIPT = re.compile(r"(\$\{CLAUDE_(?:SKILL_DIR|PLUGIN_ROOT)\}/)?((?:\.\./)*(?:[\w.-]+/)*scripts/[\w./-]*\w\.\w+)")
NAMED = re.compile(r"`([a-z0-9][a-z0-9-]*)`")


def _scripts(plugin, skill_dir, body: str) -> list:
    found = []
    for prefix, path in SCRIPT.findall(body):
        base = plugin.root if prefix.startswith("${CLAUDE_PLUGIN_ROOT}") else skill_dir
        try:
            target = safe_path(plugin.root, rel_to(plugin.root, (base / path).resolve()))
        except (PathEscape, ValueError):
            continue
        if target.is_file() and target not in found:
            found.append(target)
    return found


def rel_to(root, path) -> str:
    return path.relative_to(root.resolve()).as_posix()


def _skills(g: Graph, plugin, pid: str) -> None:
    if not plugin.skills_dir:
        return
    commands = plugins.command_skill_names(plugin.skills_dir)
    bodies = []
    for skill_md in sorted(plugin.skills_dir.glob("*/SKILL.md")):
        front, body = plugins._split(skill_md)
        name = str(front.get("name") or skill_md.parent.name)
        kind = "command" if name in commands else "skill"
        cid = g.add(Cap(kind, name, f"{plugin.id}:{name}", one_line(front.get("description")), rel(skill_md), digest(skill_md.read_bytes()),
                        plugin=plugin.id, enabled=plugin.enabled, when_to_use=one_line(front.get("when_to_use")),
                        meta={"folder": skill_md.parent.name, "argument_hint": str(front.get("argument-hint", ""))}),
                    f"{plugin.id}/{skill_md.parent.name}")
        g.link(pid, cid, "contains")
        bodies.append((cid, kind, body))
        for script in _scripts(plugin, skill_md.parent, body):
            path = rel_to(plugin.root, script)
            sid = g.add(Cap("script", path, f"{plugin.id}:{path}", f"Script named in {plugin.id}:{name}", rel(script), digest(script.read_bytes()),
                            plugin=plugin.id, enabled=plugin.enabled))
            g.link(pid, sid, "contains")
            g.link(cid, sid, "runs_script")
    for cid, kind, body in bodies:  # a command names the skills it activates in backticks, e.g. `planning-tests`
        if kind == "command":
            for named in sorted(set(NAMED.findall(body))):
                if (target := g.aliases.get(("skill", f"{plugin.id}:{named}"))) and target != cid:
                    g.link(cid, target, "applies_skill")


def _agents(g: Graph, plugin, pid: str) -> None:
    for path in sorted((plugin.root / "agents").glob("*.md")) if (plugin.root / "agents").is_dir() else []:
        front, _ = plugins._split(path)
        raw = front.get("tools") or []
        tools = [str(t).strip() for t in (raw.split(",") if isinstance(raw, str) else raw) if str(t).strip()]
        name = str(front.get("name") or path.stem)
        cid = g.add(Cap("agent", name, f"{plugin.id}:{name}", one_line(front.get("description")), rel(path), digest(path.read_bytes()),
                        plugin=plugin.id, enabled=plugin.enabled, meta={"tools": tools, "model": str(front.get("model", ""))}))
        g.link(pid, cid, "contains")


def _hooks(g: Graph, plugin, pid: str) -> None:
    for event, groups in sorted(plugin_hooks._hooks_json(plugin).items()):
        for index, group in enumerate(groups or []):
            matcher = str(group.get("matcher") or "*")
            commands = [str(h.get("command", "")) for h in group.get("hooks", []) if isinstance(h, dict)]
            name = f"{event}:{matcher}"
            text = json.dumps(group, sort_keys=True)
            cid = g.add(Cap("hook", name, f"{plugin.id}:{name}#{index}", f"{event} hook" + (f" for tools matching {matcher}" if matcher != "*" else "") + ": " + "; ".join(commands),
                            f"{rel(plugin.root)}/hooks/hooks.json", digest(text), plugin=plugin.id, enabled=plugin.enabled,
                            meta={"event": event, "matcher": matcher, "commands": commands}))
            g.link(pid, cid, "contains")


def plugin_sources(g: Graph) -> None:
    for plugin in plugins.discover():
        manifest = (plugin.root / plugin.manifest) if plugin.manifest else plugin.skills_dir or plugin.root
        text = manifest.read_text(encoding="utf-8") if manifest.is_file() else plugin.id
        pid = g.add(Cap("plugin", plugin.id, plugin.id, one_line(plugin.description), rel(manifest), digest(text), plugin=plugin.id,
                        enabled=plugin.enabled, meta={"version": plugin.version, "problems": plugin.problems}))
        _skills(g, plugin, pid)
        if plugin.id != "local-skills":  # the repository's own skills/ folder has no agents or hooks
            _agents(g, plugin, pid)
            _hooks(g, plugin, pid)
        for server in plugin.mcp_servers:  # declared in .mcp.json; an admin registers it before it can connect
            sid = g.add(Cap("mcp_server", server["name"], f"{plugin.id}:{server['name']}", f"Declared in {plugin.id}/.mcp.json, not registered",
                            f"{rel(plugin.root)}/.mcp.json", digest(json.dumps(server, sort_keys=True, default=str)), plugin=plugin.id, enabled=False,
                            profiles=",".join(mcp.STDIO_PROFILES) if server["transport"] == "stdio" else ALL_PROFILES,
                            meta={"transport": server["transport"], "declared": True}))
            g.link(pid, sid, "contains")


def mcp_sources(g: Graph) -> None:
    """Registered servers and only the tools their real list_tools stored. Every MCP tool needs approval (code_sources.RISKY rule)."""
    for server in mcp.all_servers():
        profiles = ",".join(mcp.STDIO_PROFILES) if server["transport"] == "stdio" else ALL_PROFILES
        facts = {k: server.get(k) for k in ("name", "transport", "command", "args", "url", "status", "plugin_id")}
        sid = g.add(Cap("mcp_server", server["name"], server["name"], f"{server['transport']} MCP server, {server['status']}", "mcp_servers",
                        digest(json.dumps(facts, sort_keys=True)), plugin=server.get("plugin_id"), profiles=profiles,
                        enabled=server["status"] == mcp.CONNECTED, key=server["id"], meta={"server_id": server["id"], "transport": server["transport"]}))
        if pid := g.aliases.get(("plugin", server.get("plugin_id") or "")):  # plugins are read first
            g.link(pid, sid, "contains")
        for tool in mcp.tools(server["id"]):
            text = json.dumps([tool["name"], tool["description"], tool["parameters_schema"]])
            tid = g.add(Cap("mcp_tool", tool["name"], f"{server['name']}:{tool['name']}", one_line(tool["description"]), "mcp_tools", digest(text),
                            plugin=server.get("plugin_id"), needs_approval=True, profiles=profiles, enabled=server["status"] == mcp.CONNECTED,
                            key=f"{server['id']}:{tool['name']}", meta={"server_id": server["id"]}))
            g.link(sid, tid, "serves")
