"""Capability registry (plan Phase R): every tool, agent, skill, command, workflow and how they connect, derived by a sync.

`sync()` rebuilds it; `listing`, `detail` and `tree` read it per user; `find_capability`, `describe_capability` and
`index_text` are what the harness calls.
"""
from __future__ import annotations

from backend.core.registry.read import detail, listing, tree  # noqa: F401
from backend.core.registry.search import describe_capability, find_capability, index_text  # noqa: F401
from backend.core.registry.store import latest  # noqa: F401
from backend.core.registry.sync import sync  # noqa: F401
