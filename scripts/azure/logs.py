"""Prefixed loggers. The entry scripts print different prefixes, so each builds its own."""
from __future__ import annotations

import sys


def make_logger(prefix: str):
    def log(msg: str) -> None:
        print(f"[{prefix}] {msg}", flush=True)

    def warn(msg: str) -> None:
        print(f"[{prefix} WARNING] {msg}", flush=True)

    def error(msg: str) -> None:
        print(f"[{prefix} ERROR] {msg}", file=sys.stderr, flush=True)

    return log, warn, error
