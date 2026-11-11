"""Platform-wide sandbox slots for the harness on the web profile (plan H2, decision D1).

Every shell command and file write the harness runs on the shared web server holds one row of `sandbox_leases` while it
runs, so at most `ATLAS_MAX_SANDBOXES` (default 5) run at once across all projects and people. A call beyond that is
refused with a message that names the queue and how full it is; the model gets that text as the tool result. Desktop and
local profiles are one person's machine and take no lease.
ponytail: refuse-when-full, no waiting queue; add a FIFO wait with a position when users need it.
"""
from __future__ import annotations

import time
from contextlib import contextmanager

from backend import config
from backend.core.errors import AqeError
from backend.db import db, new_id, now


class SandboxBusy(AqeError):
    code = "AQE-SANDBOX-BUSY"
    action = "Wait for a running command or write to finish, then ask again."


def busy_message(running: int) -> str:
    return (f"Sandbox queue full: all {config.MAX_SANDBOXES} platform sandbox slots are in use ({running} running). "
            "Nothing ran. Try again when one finishes.")


@contextmanager
def lease(kind: str, project_id: str, thread_id: str, user_id: str | None):
    """Holds one slot for the duration of the block on the web profile; elsewhere it does nothing."""
    if config.PROFILE != "web":
        yield None
        return
    lease_id = new_id("lse")
    with db() as con:
        con.execute("BEGIN IMMEDIATE")  # count and insert as one step, so two callers cannot both take the last slot
        con.execute("DELETE FROM sandbox_leases WHERE expires_at < ?", (time.time(),))
        running = con.execute("SELECT COUNT(*) FROM sandbox_leases").fetchone()[0]
        if running >= config.MAX_SANDBOXES:
            raise SandboxBusy(busy_message(running))
        con.execute("INSERT INTO sandbox_leases VALUES (?,?,?,?,?,?,?)",
                    (lease_id, project_id, thread_id, user_id, kind, now(), time.time() + config.HARNESS_SHELL_TIMEOUT + 60))
    try:
        yield lease_id
    finally:
        with db() as con:
            con.execute("DELETE FROM sandbox_leases WHERE id=?", (lease_id,))
