"""The sync: derive every capability from code and manifests, with no model call, and replace the registry tables.

Call `sync()` at startup and after anything that changes what exists: a plugin install, enable or disable, a skill
publish or delete, an MCP connect, a grant change. A source that fails is reported in the version row and its
capabilities are absent; nothing stands in for them.
"""
from __future__ import annotations

import logging
import threading

from backend.core.registry import code_sources, plugin_sources, store, workflow_sources
from backend.core.registry.model import Graph
from backend.core.security import redact

LOG = logging.getLogger("aqe.registry")
_LOCK = threading.Lock()
# order matters: links resolve at the end, and harness_delegations reads the plugin agents plugin_sources added
SOURCES = (code_sources.platform_tools, code_sources.maf_builtins, code_sources.agents, plugin_sources.plugin_sources,
           plugin_sources.mcp_sources, workflow_sources.gate_sources, workflow_sources.workflow_sources, code_sources.harness_delegations)


def build() -> tuple[Graph, list[str]]:
    g, problems = Graph(), []
    for source in SOURCES:
        try:
            source(g)
        except Exception as exc:  # one broken source must not hide the others; it is named in the version row
            problems.append(redact(f"{source.__name__}: {type(exc).__name__}: {exc}"))
            LOG.warning("registry source %s failed: %s", source.__name__, problems[-1])
    g.resolve()
    return g, problems + g.unresolved


def sync(by: str = "system") -> dict:
    with _LOCK:
        g, problems = build()
        version = store.write(g, by, problems)
    LOG.info("registry synced: %s capabilities, %s links, hash %s", version["capabilities"], version["links"], version["hash"][:12])
    return version
