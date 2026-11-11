"""The governed specialists the harness delegates to through MAF's `BackgroundAgentsProvider` (HS-11).

Each child is built by `runtime.build`, so it gets its own enabled check, model allowance, deny-by-default tools,
`tool_audit` rows and telemetry under its own agent key. Children only read: the risky tools (writes, test runs,
workflow starts) are never handed to them, and no tool anywhere decides a gate or an approval.
"""
from __future__ import annotations

import logging

from backend.core.auth import Forbidden
from backend.core.errors import AqeError
from backend.maf import governance, tools
from backend.maf import runtime
from backend.maf.harness_kit.catalog import RISKY

SPECIALISTS = ("test-design-architect", "requirements-analyst", "repo-intelligence-analyst", "principal-test-architect", "confidence-reviewer")


def build(project_id: str, user_id: str | None) -> list:
    """One MAF agent per specialist this user may run now. A disabled agent or a refused model is left out, and logged."""
    found = []
    readable = [t for t in tools.document_tools(project_id) if t.name not in RISKY]
    for key in SPECIALISTS:
        try:
            agent = runtime.build(key, project_id, readable, chat=True, source="chat", user_id=user_id)
        except (AqeError, Forbidden) as exc:
            logging.getLogger("aqe.chat").info("harness: specialist %s left out: %s", key, exc)
            continue
        agent.description = governance.POLICIES[key].purpose  # what the parent reads in the background-agent list
        found.append(agent)
    return found
