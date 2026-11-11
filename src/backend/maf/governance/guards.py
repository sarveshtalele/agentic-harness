"""Guardrails: secret redaction, prompt-injection removal, typed errors, and the guardrail event log."""
from __future__ import annotations

import re

from backend.core.errors import AqeError, classify
from backend.core.security import redact, scan_secrets
from backend.db import db, now

INJECTION = re.compile(
    r"(?:ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules)"
    r"|disregard\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|your)\s+(instructions|prompts|rules)"
    r"|forget\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules)"
    r"|override\s+(all\s+|any\s+)?(the\s+)?(system\s+|safety\s+|security\s+)?(prompt|prompts|instructions|rules|guardrails|policies)"
    r"|reveal\s+(your\s+|the\s+)?(system\s+|hidden\s+)?(prompt|instructions)"
    r"|you\s+are\s+now\s+(a|an|in)\b"
    r"|(?:enter|enable|activate)\s+developer\s+mode\b"
    r"|(?:dan\s+mode|do\s+anything\s+now)\b"
    r"|bypass\s+(all\s+)?(safety|security|guardrails|content\s+filters)\b"
    r"|jailbreak\b"
    r"|send\s+.{0,40}(api[_ ]?key|token|credential|secret).{0,40}\bto\b"
    r")[^\n.]*\.?",  # the whole sentence goes, or its tail still gives the order
    re.I,
)


def flag(agent: str, kind: str, action: str, detail: str, project_id: str | None = None, run_id: str | None = None) -> None:
    with db() as con:
        con.execute("INSERT INTO guardrail_events (agent, project_id, run_id, kind, action, detail, created_at) VALUES (?,?,?,?,?,?,?)",
                    (agent, project_id, run_id, kind, action, redact(detail)[:500], now()))


REMOVED = "[removed by Agentic QE Platform: possible prompt injection]"


def guard_text(agent: str, text: str, direction: str, project_id: str | None, run_id: str | None = None) -> str:
    """Input and output guardrail. Secrets and likely prompt injection never reach the model or the record."""
    hits = scan_secrets(text)
    if hits:
        flag(agent, "secret", "redacted", f"{direction}: {sorted({h['type'] for h in hits})}", project_id, run_id)
        text = redact(text)
    return neutralize(agent, text, direction, project_id, run_id)


def neutralize(agent: str, text: str, where: str, project_id: str | None, run_id: str | None = None) -> str:
    """Remove injection attempts from untrusted text. Model providers may also reject such text outright, failing the call."""
    matches = [m.group(0) for m in INJECTION.finditer(text)]
    if not matches:
        return text
    flag(agent, "prompt_injection", "removed", f"{where}: {matches[0]}", project_id, run_id)
    return INJECTION.sub(REMOVED, text)


def typed_error(agent: str, exc: Exception, project_id: str | None, run_id: str | None = None) -> AqeError:
    """Turn any failure into a typed error. A provider refusal is also recorded as a guardrail event."""
    error = classify(exc)
    if error.code == "AQE-MODEL-005":
        flag(agent, "provider_filter", "blocked", error.message, project_id, run_id)
    return error


def explain_error(agent: str, exc: Exception, project_id: str | None, run_id: str | None = None) -> str:
    """The sentence a person can act on, for places that show text only."""
    return typed_error(agent, exc, project_id, run_id).message


def guard_tool_result(agent: str, tool: str, result, project_id: str | None, run_id: str | None):
    """Repository text is untrusted, so tool results pass the same filter before the model reads them."""
    if isinstance(result, str):
        return neutralize(agent, result, f"tool {tool}", project_id, run_id)
    for content in result if isinstance(result, list) else []:  # MAF wraps tool output in Content objects
        if getattr(content, "type", "") == "text" and content.text:
            content.text = neutralize(agent, content.text, f"tool {tool}", project_id, run_id)
    return result
