"""The process-wide model gate: bounds concurrent model calls."""
from __future__ import annotations

import asyncio
import weakref

from backend.config import MODEL_CONCURRENCY


_gates: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _model_gate() -> asyncio.Semaphore:
    """Bound concurrent model calls for the process, so parallel workflows queue instead of exhausting a small server."""
    loop = asyncio.get_running_loop()
    return _gates.setdefault(loop, asyncio.Semaphore(MODEL_CONCURRENCY))
