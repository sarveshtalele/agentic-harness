"""Agent governance: one registry, per-agent tool policy, an admin kill switch, guardrails, and call telemetry."""
from __future__ import annotations

from backend.core import prompts  # noqa: F401 - re-exported; tests read governance.prompts
from backend.maf.agents import CHAT_READ, DOCS, POLICIES, READ, AgentPolicy  # noqa: F401 - re-exported
from backend.maf.governance.calls import SKILL_TOOLS, _record_refused_tools, _tool_count, record_call, recent_calls, telemetry  # noqa: F401
from backend.maf.governance.guards import INJECTION, REMOVED, explain_error, flag, guard_text, guard_tool_result, neutralize, typed_error  # noqa: F401
from backend.maf.governance.policy import AgentDisabled, allowed, require_enabled, settings, token_limit, update_settings  # noqa: F401
from backend.maf.governance.registry import overview, recent_events  # noqa: F401
