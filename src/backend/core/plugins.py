"""Plugin discovery: `plugins/*/` folders plus the repo's own `skills/` as the implicit plugin "local-skills".

A manifest is our `plugin.json`, the Claude Code `.claude-plugin/plugin.json`, or a root `plugin.json` in agents format.
Plugin text is trusted platform content (first-party, in this repo). Every manifest path goes through `safe_path`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend.config import ROOT, SKILLS_DIR
from backend.core.security import PathEscape, safe_path

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


def _plugin(folder: Path) -> Plugin:
    rel, data, problems = _read_manifest(folder)
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
    return Plugin(str(data.get("id") or data.get("name") or folder.name), str(data.get("version", "")), str(data.get("description", "")),
                  "first-party", "repo", folder, skills_dir, rel, problems)


def discover(root: Path | None = None) -> list[Plugin]:
    # ponytail: rescans per call; cache with mtime if it gets slow
    base = (root or ROOT).resolve()
    local = Plugin("local-skills", "", "Skills in the repository skills/ folder", "first-party", "repo", SKILLS_DIR.parent,
                   SKILLS_DIR if SKILLS_DIR.is_dir() else None, "", [] if SKILLS_DIR.is_dir() else ["skills folder not found"])
    folders = sorted(p for p in (base / "plugins").glob("*") if p.is_dir()) if (base / "plugins").is_dir() else []
    return [local, *(_plugin(p) for p in folders)]


def command_skill_names(skills_dir: Path) -> set[str]:
    """Skill folders whose SKILL.md frontmatter sets `disable-model-invocation: true` (slash commands). MAF drops that field, so read it raw."""
    names: set[str] = set()
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---") or "\n---" not in text:
            continue
        try:
            front = yaml.safe_load(text[3:].split("\n---", 1)[0])
        except yaml.YAMLError:
            continue
        if isinstance(front, dict) and front.get("disable-model-invocation") is True:
            names.add(str(front.get("name") or skill_md.parent.name))
    return names


def skill_paths(root: Path | None = None) -> list[Path]:
    seen: list[Path] = []
    for plugin in discover(root):
        if plugin.skills_dir and plugin.skills_dir not in seen:
            seen.append(plugin.skills_dir)
    return seen
