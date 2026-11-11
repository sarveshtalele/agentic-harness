"""Failure records: one redacted diagnostic row per failure, and the hand-off from a stage to the run guard."""
from __future__ import annotations

import logging

from backend.config import RUNS
from backend.core.errors import classify, stack_of
from backend.core.security import redact, safe_path
from backend.db import db, new_id, now
from backend.maf.engine.run_context import RunContext


_failures: dict[str, dict] = {}
log = logging.getLogger("aqe.engine")


def record_failure(run_id: str, stage: str, exc: BaseException) -> dict:
    """One diagnostic row per failure, redacted. The whole rejected reply goes to a file under the run, never into a column."""
    error = classify(exc)
    d = error.detail
    error_id = new_id("err")
    reply_file = ""
    if d.get("reply"):
        reply_file = f"failures/{error_id}-reply.txt"
        path = safe_path(RUNS / run_id, reply_file, for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(redact(str(d["reply"])), encoding="utf-8")
    failure = {
        "id": error_id, "run_id": run_id, "code": error.code, "message": redact(error.message), "action": error.action, "retryable": int(error.retryable), "stage": stage,
        "agent": d.get("agent", ""), "attempt": d.get("attempt"), "prompt_ref": d.get("prompt_ref", ""), "model": d.get("model", ""), "finish_reason": d.get("finish_reason", ""),
        "tokens_in": d.get("tokens_in"), "tokens_out": d.get("tokens_out"), "duration_ms": d.get("duration_ms"), "parse_pos": d.get("parse_pos"),
        "parse_context": redact(d.get("parse_context", "")), "technical": redact(str(d.get("technical", "")))[:2000], "reply_file": reply_file,
        "stack": stack_of(exc), "provider_status": d.get("provider_status"), "provider_request_id": redact(str(d.get("provider_request_id", ""))), "created_at": now(),
    }
    with db() as con:
        con.execute(f"INSERT INTO run_failures ({', '.join(failure)}) VALUES ({', '.join('?' * len(failure))})", tuple(failure.values()))
    log.error("run %s stage %s failed: %s error_id=%s %s", run_id, stage, error.code, error_id, failure["message"],
              extra={"fields": {"run_id": run_id, "stage": stage, "agent": failure["agent"], "error_id": error_id, "code": error.code}})
    return failure


async def _safely(rc: RunContext, awaitable):
    """MAF reduces executor failures to the exception type, so the real failure is recorded here and handed to _guarded."""
    try:
        return await awaitable
    except Exception as exc:
        failure = _failures[rc.run_id] = record_failure(rc.run_id, rc.stage, exc)
        rc.log(f"{failure['code']} {failure['message']}", {"error_id": failure["id"], "code": failure["code"]}, kind="error")
        raise
