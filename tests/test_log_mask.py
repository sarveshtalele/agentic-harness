"""The log mask redacts secrets without breaking formatters that read record.args (uvicorn's access log)."""
from __future__ import annotations

import logging

from backend.core import security


def _record(msg: str, args: tuple) -> logging.LogRecord:
    security.install_log_mask()
    return logging.getLogRecordFactory()("t", logging.INFO, __file__, 1, msg, args, None)


def test_plain_access_line_keeps_its_args():
    args = ("127.0.0.1:1", "GET", "/api/health", "1.1", 200)
    rec = _record('%s - "%s %s HTTP/%s" %d', args)
    assert rec.args == args  # uvicorn's AccessFormatter unpacks exactly these five
    assert rec.getMessage() == '127.0.0.1:1 - "GET /api/health HTTP/1.1" 200'


def test_secret_in_args_is_masked_and_args_dropped():
    secret = "sk-" + "a" * 40
    rec = _record("key %s", (secret,))
    assert secret not in rec.getMessage() and rec.args == ()
