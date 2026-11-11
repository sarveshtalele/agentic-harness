"""Progressive tool discovery for the harness (plan M4).

The model starts with a small core. Everything else its policy allows, plus the MCP tools the user's role was granted
on connected servers, sits in a catalogue. Every run lists the catalogue's names and one-line purposes in the instructions
(deferred tools, as Claude Code does); the model loads schemas with `load_tools`, and `find_tools` searches long catalogues. Loaded names are
kept per thread in `data/harness/<project>/tools/<thread>.json`, and `LoadedTools` (a MAF ContextProvider, the way
`SkillsProvider` adds `load_skill`) puts them back on every later run. Only catalogue names can be loaded, so a tool
the policy denies can never be loaded.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from agent_framework import ContextProvider

from backend.core import ledger
from backend.core.mcp import registry as mcp_registry

# read-only tools the harness needs on most turns; everything else is found and loaded on demand
CORE = frozenset({"list_files", "read_file", "grep", "list_documents", "read_document", "search_documents",
                  "scan_repository", "sandbox_status", "list_findings"})
# These write or run code, so a human approves each call (MAF ToolApprovalMiddleware). Every MCP tool is treated the same.
RISKY = frozenset({"start_workflow", "run_tests", "save_document", "remember", "create_skill"})
THREAD_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def one_line(text: str | None) -> str:
    lines = (text or "").strip().splitlines()
    return lines[0][:160] if lines else ""


class Catalogue:
    """Every tool this harness may load: platform tools beyond the core, and granted MCP tools by server."""

    def __init__(self, platform_tools: list, mcp_servers: list):
        self.tools = {t.name: t for t in platform_tools}
        self.mcp: dict[str, tuple] = {}  # tool name -> (that server's MAF MCP tool, one-line description)
        for server in mcp_servers:
            server.approval_mode = "always_require"
            granted = set(server.allowed_tools or ())
            for listed in mcp_registry.tools(server.name):  # stored from the server's real list_tools
                if listed["name"] in granted and listed["name"] not in self.tools:  # ponytail: a name clash keeps the platform tool
                    self.mcp[listed["name"]] = (server, one_line(listed.get("description")))

    def __contains__(self, name: str) -> bool:
        return name in self.tools or name in self.mcp

    def descriptions(self) -> dict[str, str]:
        return {**{n: one_line(t.description) for n, t in self.tools.items()}, **{n: d for n, (_, d) in self.mcp.items()}}

    def search(self, query: str) -> list[dict]:
        words = query.lower().split()
        found = [{"name": n, "description": d, "source": "mcp" if n in self.mcp else "platform"}
                 for n, d in sorted(self.descriptions().items()) if not words or any(w in f"{n} {d}".lower() for w in words)]
        return found

    def resolve(self, names) -> list:
        """The tool objects for loaded names. An MCP server is offered limited to the names loaded from it."""
        found = [self.tools[n] for n in names if n in self.tools]
        servers: dict[int, tuple] = {}
        for name in names:
            if name in self.mcp:
                server = self.mcp[name][0]
                servers.setdefault(id(server), (server, []))[1].append(name)
        for server, picked in servers.values():
            server.allowed_tools = picked
            found.append(server)
        return found


class LoadedTools(ContextProvider):
    """Adds the thread's loaded tools to every run. MCP servers among them are connected by MAF at run start."""

    def __init__(self, folder: Path, project_id: str, thread_id: str, catalogue: Catalogue):
        super().__init__("harness-loaded-tools")
        if not THREAD_ID.match(thread_id):  # thread ids are platform ids; this keeps the file name inside the folder
            raise ValueError("Unexpected thread id")
        self.path, self.project_id, self.thread_id, self.catalogue = folder / f"{thread_id}.json", project_id, thread_id, catalogue

    def names(self) -> list[str]:
        stored = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else []
        return [n for n in stored if n in self.catalogue]  # a tool the policy or a grant no longer allows drops out

    def add(self, names: list[str]) -> list[str]:
        merged = list(dict.fromkeys(self.names() + names))
        self.path.write_text(json.dumps(merged), encoding="utf-8")
        ledger.append(self.project_id, "agent:harness", "harness.tools_loaded", self.thread_id, {"names": names})
        return merged

    async def before_run(self, *, agent, session, context, state) -> None:
        # The model can only call what it knows exists: list every loadable tool by name and purpose; schemas stay deferred
        loaded = set(self.names())
        index = [f"- {n}: {d}" for n, d in sorted(self.catalogue.descriptions().items()) if n not in loaded]
        if index:
            context.extend_instructions(self.source_id, "Tools you can load with load_tools (exact names; each stays loaded for this chat):\n" + "\n".join(index))
        if tools := self.catalogue.resolve(sorted(loaded)):
            context.extend_tools(self.source_id, tools)
