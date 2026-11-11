"""The workflow registry: workflow files add their definitions here, and it is filled on first use."""
from __future__ import annotations

import logging
from typing import Callable

from backend.maf.engine.specs import Definition


REGISTRY: dict[str, Callable[[], Definition]] = {}


def _ensure_workflows() -> None:
    if not REGISTRY:
        try:
            import backend.maf.workflows  # noqa: F401
        except Exception as exc:
            logging.getLogger("aqe.engine").warning("Failed to dynamically import workflows: %s", exc)
