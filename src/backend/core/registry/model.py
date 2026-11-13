"""The registry in memory during one sync: capabilities by id, links by id, and links still to resolve by kind and name.

An id is a hash of kind and key, so the same source always gives the same id and two syncs give the same table.
A link to a name no source produced is dropped and reported, never invented.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from backend.config import ROOT
from backend.core.security import sha256

ALL_PROFILES = "web,local"
RELATIONS = ("contains", "performed_by", "uses_tool", "applies_skill", "runs_script", "delegates_to", "serves", "gates")


def cap_id(kind: str, key: str) -> str:
    return "cap_" + hashlib.sha256(f"{kind}:{key}".encode()).hexdigest()[:16]


def rel(path) -> str:
    """A source path relative to the repository, with forward slashes on every system."""
    try:
        return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def one_line(text) -> str:
    return " ".join(str(text or "").split())


def digest(text: str | bytes) -> str:
    return sha256(text)


@dataclass
class Cap:
    kind: str
    name: str
    qualified_name: str
    description: str = ""
    source: str = ""
    sha256: str = ""
    plugin: str | None = None
    risk: str = ""
    needs_approval: bool = False
    profiles: str = ALL_PROFILES
    enabled: bool = True
    when_to_use: str = ""
    meta: dict = field(default_factory=dict)
    key: str = ""  # identity when the qualified name is not unique (an MCP server's id)

    @property
    def id(self) -> str:
        return cap_id(self.kind, self.key or self.qualified_name)


class Graph:
    def __init__(self):
        self.caps: dict[str, Cap] = {}
        self.links: set[tuple[str, str, str, str]] = set()
        self.aliases: dict[tuple[str, str], str] = {}
        self.pending: list[tuple[str, str, str, str, str]] = []
        self.unresolved: list[str] = []

    def add(self, cap: Cap, *aliases: str) -> str:
        self.caps.setdefault(cap.id, cap)
        for alias in (cap.qualified_name, *aliases):
            self.aliases.setdefault((cap.kind, alias), cap.id)
        return cap.id

    def link(self, src: str, dst: str, relation: str, detail="") -> None:
        assert relation in RELATIONS, relation
        self.links.add((src, dst, relation, str(detail)))

    def link_to(self, src: str, kind: str, key: str, relation: str, detail="") -> None:
        """A link to a capability named by kind and qualified name or alias, resolved once every source has run."""
        self.pending.append((src, kind, key, relation, str(detail)))

    def resolve(self) -> None:
        for src, kind, key, relation, detail in self.pending:
            dst = self.aliases.get((kind, key))
            if dst:
                self.link(src, dst, relation, detail)
            else:
                self.unresolved.append(f"{self.caps[src].qualified_name} {relation} {kind} {key}: no source defines it")
        self.pending = []
